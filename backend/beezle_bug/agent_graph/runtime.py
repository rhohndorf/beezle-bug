"""
AgentGraphRuntime - manages the runtime state of a deployed agent graph.

Responsibilities:
- Deploy/undeploy agent graphs
- Manage live agent, KG, memory stream instances
- Route messages between connected nodes
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable, List, Dict
from loguru import logger

from .types import NodeType, EdgeType
from .node import Node
from .edge import Edge
from .agent_graph import AgentGraph
from .agent import Agent

from beezle_bug.memory.knowledge_graph import KnowledgeGraph
from beezle_bug.memory.memory_stream import MemoryStream
from beezle_bug.events import EventBus, EventType
from beezle_bug.scheduler import Scheduler
from beezle_bug.template import TemplateLoader
from beezle_bug.tools.toolbox_factory import ToolboxFactory
from beezle_bug.tools import Tool
from beezle_bug.llm_adapter import OpenAiAdapter
from beezle_bug.storage import StorageService


@dataclass
class WaitAndCombineState:
    """Runtime state for a WaitAndCombine node."""
    expected_senders: set[str] = field(default_factory=set)  # Node IDs of expected senders
    senders_received: set[str] = field(default_factory=set)  # Node IDs that have sent
    pending_messages: List[Dict[str, str]] = field(default_factory=list)  # Accumulated messages


def create_delegate_tool(agents_dict: dict, target_node_id: str, target_name: str, source_name: str) -> type[Tool]:
    """
    Create a delegate tool class that calls another agent synchronously.
    
    Args:
        agents_dict: Reference to the runtime's agents dict (for runtime lookup)
        target_node_id: The node ID of the target agent
        target_name: The display name of the target agent
        source_name: The name of the calling agent (for attribution)
    
    Returns:
        A Tool class that, when called, asks the target agent a question
    """
    # Sanitize target name for use as function name
    safe_name = target_name.lower().replace(' ', '_').replace('-', '_')
    tool_name = f"ask_{safe_name}"
    
    class DelegateTool(Tool):
        question: str
        
        def run(self, agent) -> str:
            target_agent = agents_dict.get(target_node_id)
            if not target_agent:
                return f"Error: Agent '{target_name}' is not available"
            # Use list-based message format
            messages = [{"sender": source_name, "content": self.question}]
            response_messages = target_agent.process_message(messages)
            if response_messages:
                return response_messages[0]["content"]
            return "No response from agent"
    
    DelegateTool.__name__ = tool_name
    DelegateTool.__doc__ = f"Ask {target_name} a question and get their response. Use this when you need {target_name}'s expertise or input."
    
    return DelegateTool


class AgentGraphRuntime:
    """Manages the runtime state of a deployed agent graph."""

    def __init__(
        self,
        storage: StorageService,
        event_bus: EventBus,
        scheduler: Scheduler,
        template_loader: TemplateLoader,
        toolbox_factory: ToolboxFactory,
        on_agent_graph_message: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.storage = storage
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.template_loader = template_loader
        self.toolbox_factory = toolbox_factory
        self.on_agent_graph_message = on_agent_graph_message

        # Deployment state
        self.is_deployed: bool = False
        self._current_project_id: Optional[str] = None
        self._current_agent_graph: Optional[AgentGraph] = None

        # Runtime instances (keyed by node ID) - only populated when deployed
        self.agents: dict[str, Agent] = {}
        self.knowledge_graphs: dict[str, KnowledgeGraph] = {}
        self.memory_streams: dict[str, MemoryStream] = {}
        self.toolboxes: dict[str, list[str]] = {}
        self.wait_and_combine_states: dict[str, WaitAndCombineState] = {}

        # Subscribe to events for message routing
        self.event_bus.subscribe(EventType.MESSAGE_SENT, self._on_agent_message)
        self.event_bus.subscribe(EventType.MESSAGE_RECEIVED, self._on_agent_response)

    # === Deploy / Undeploy ===

    def deploy(self, agent_graph: AgentGraph, project_id: str) -> None:
        """Deploy an agent graph - instantiate all nodes."""
        if self.is_deployed:
            logger.warning("Already deployed, undeploying first")
            self.undeploy()

        self._current_agent_graph = agent_graph
        self._current_project_id = project_id

        logger.info(f"Deploying agent graph for project {project_id}")
        self._instantiate_agent_graph(agent_graph)
        self.is_deployed = True
        logger.info(f"Agent graph deployed for project {project_id}")

    def undeploy(self) -> None:
        """Undeploy - stop all runtime instances."""
        if not self.is_deployed or not self._current_agent_graph:
            return

        logger.info("Undeploying agent graph")

        # Stop all scheduled events first
        for node in self._current_agent_graph.nodes:
            if node.type == NodeType.SCHEDULED_EVENT:
                self._stop_scheduled_event_node(node.id)

        # Stop all agents
        for agent_id in list(self.agents.keys()):
            self._stop_agent_node(agent_id)

        # Persist all node data before clearing
        self.persist_all()

        # Clear resources
        self.knowledge_graphs.clear()
        self.memory_streams.clear()
        self.toolboxes.clear()
        self.wait_and_combine_states.clear()

        self._current_agent_graph = None
        self._current_project_id = None
        self.is_deployed = False
        logger.info("Agent graph undeployed")

    # === Agent Graph Instantiation ===

    def _instantiate_agent_graph(self, agent_graph: AgentGraph) -> None:
        """Instantiate all nodes in an agent graph."""
        # First pass: create resources (KGs, Memory Streams, Toolboxes)
        for node in agent_graph.nodes:
            if node.type == NodeType.KNOWLEDGE_GRAPH:
                self._create_kg_node(node)
            elif node.type == NodeType.MEMORY_STREAM:
                self._create_memory_stream_node(node)
            elif node.type == NodeType.TOOLBOX:
                self._create_toolbox_node(node)

        # Second pass: create agents (which may connect to resources)
        for node in agent_graph.nodes:
            if node.type == NodeType.AGENT:
                self._create_agent_node(node, agent_graph)

        # Third pass: create scheduled events (which connect to agents)
        for node in agent_graph.nodes:
            if node.type == NodeType.SCHEDULED_EVENT:
                self._start_scheduled_event_node(node, agent_graph)

        # Fourth pass: create WaitAndCombine nodes (which can connect from/to agents)
        for node in agent_graph.nodes:
            if node.type == NodeType.WAIT_AND_COMBINE:
                self._create_wait_and_combine_node(node, agent_graph)

    def _create_kg_node(self, node: Node) -> KnowledgeGraph:
        """Create a Knowledge Graph instance for a node."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Knowledge Graph")

        # Load persisted KG data if exists, otherwise create new
        kg = None
        if self._current_project_id:
            kg = self.storage.load_knowledge_graph(self._current_project_id, node.id)
        
        if kg is None:
            kg = KnowledgeGraph()

        self.knowledge_graphs[node.id] = kg
        logger.info(f"Created KG node: {name} ({node.id})")
        return kg

    def _create_memory_stream_node(self, node: Node) -> MemoryStream:
        """Create a Memory Stream instance for a node."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Memory Stream")

        # Load persisted data if exists, otherwise create new
        ms = None
        if self._current_project_id:
            ms = self.storage.load_memory_stream(self._current_project_id, node.id)
        
        if ms is None:
            ms = MemoryStream()

        self.memory_streams[node.id] = ms
        logger.info(f"Created Memory Stream node: {name} ({node.id})")
        return ms

    def _create_toolbox_node(self, node: Node) -> list[str]:
        """Create a Toolbox config for a node (stores tool names)."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Toolbox")
        tools = config.get("tools", [])

        self.toolboxes[node.id] = tools
        logger.info(f"Created Toolbox node: {name} ({node.id}) with {len(tools)} tools")
        return tools

    def _create_agent_node(self, node: Node, agent_graph: AgentGraph) -> Agent:
        """Create an Agent instance for a node."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()

        # Find connected KG, Memory Stream, and Toolbox via edges
        kg = None
        memory_stream = None
        tools = []

        for edge in agent_graph.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.RESOURCE:
                continue

            resource_node_id = (
                edge.target_node if edge.source_node == node.id else edge.source_node
            )
            resource_node = agent_graph.get_node(resource_node_id)

            if resource_node and resource_node.type == NodeType.KNOWLEDGE_GRAPH:
                kg = self.knowledge_graphs.get(resource_node_id)
            elif resource_node and resource_node.type == NodeType.MEMORY_STREAM:
                memory_stream = self.memory_streams.get(resource_node_id)
            elif resource_node and resource_node.type == NodeType.TOOLBOX:
                toolbox_tools = self.toolboxes.get(resource_node_id, [])
                tools.extend(toolbox_tools)

        # Extract config values
        name = config.get("name", "Agent")
        model = config.get("model", "gpt-4")
        api_url = config.get("api_url", "http://127.0.0.1:1234/v1")
        api_key = config.get("api_key", "")
        system_template_name = config.get("system_template", "agent")

        # Create toolbox from connected Toolbox node(s)
        toolbox = self.toolbox_factory(tools)

        # Find DELEGATE edges and create delegate tools
        for edge in agent_graph.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.DELEGATE:
                continue
            if edge.source_node != node.id or edge.source_port != "ask":
                continue

            target_node = agent_graph.get_node(edge.target_node)
            if target_node and target_node.type == NodeType.AGENT:
                target_config = target_node.config if isinstance(target_node.config, dict) else target_node.config.model_dump()
                target_name = target_config.get("name", "Agent")

                delegate_tool = create_delegate_tool(
                    agents_dict=self.agents,
                    target_node_id=edge.target_node,
                    target_name=target_name,
                    source_name=name
                )
                toolbox.tools[delegate_tool.__name__] = delegate_tool
                logger.info(f"Added delegate tool '{delegate_tool.__name__}' to {name}")

        # Load template
        template = self.template_loader.load(system_template_name)

        # Create LLM adapter
        adapter = OpenAiAdapter(
            model=model,
            api_url=api_url,
            api_key=api_key,
        )

        # Create agent
        agent = Agent(
            id=node.id,
            name=name,
            adapter=adapter,
            toolbox=toolbox,
            event_bus=self.event_bus,
            memory_stream=memory_stream if memory_stream is not None else MemoryStream(),
            knowledge_graph=kg if kg is not None else KnowledgeGraph(),
            system_template=template,
        )

        self.agents[node.id] = agent
        logger.info(f"Created Agent node: {name} ({node.id})")
        return agent

    def _stop_agent_node(self, node_id: str) -> None:
        """Stop and clean up an agent node."""
        if node_id in self.agents:
            del self.agents[node_id]
            logger.info(f"Stopped agent node: {node_id}")

    def _start_scheduled_event_node(self, node: Node, agent_graph: AgentGraph) -> None:
        """Start a Scheduled Event node that sends messages to connected nodes."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Scheduled Event")
        trigger_type = config.get("trigger_type", "interval")
        run_at_str = config.get("run_at")
        interval_seconds = config.get("interval_seconds", 30)
        message_content = config.get("message_content", "Review your current state and pending tasks.")

        # Find connected targets (agents or WaitAndCombine) via MESSAGE edges from message_out port
        target_info: List[Dict[str, Any]] = []  # [{node_id, node_type}, ...]
        for edge in agent_graph.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.MESSAGE:
                continue
            if edge.source_node != node.id or edge.source_port != "message_out":
                continue
            target_node = agent_graph.get_node(edge.target_node)
            if target_node and target_node.type in (NodeType.AGENT, NodeType.WAIT_AND_COMBINE):
                target_info.append({"node_id": edge.target_node, "node_type": target_node.type})

        if not target_info:
            logger.warning(f"Scheduled Event '{name}' ({node.id}) has no connected targets")
            return

        task_id = f"{node.id}_scheduled"
        scheduled_event_node_id = node.id

        def scheduled_tick(targets=target_info, event_name=name, content=message_content):
            messages = [{"sender": event_name, "content": content}]
            
            for target in targets:
                target_id = target["node_id"]
                target_type = target["node_type"]
                
                if target_type == NodeType.AGENT:
                    agent = self.agents.get(target_id)
                    if agent:
                        target_node = agent_graph.get_node(target_id)
                        agent_name = "Agent"
                        if target_node:
                            agent_config = target_node.config if isinstance(target_node.config, dict) else target_node.config.model_dump()
                            agent_name = agent_config.get("name", "Agent")

                        response_messages = agent.process_message(messages)
                        if response_messages:
                            self._route_messages(target_id, agent_name, response_messages)
                
                elif target_type == NodeType.WAIT_AND_COMBINE:
                    self._deliver_to_wait_and_combine(target_id, scheduled_event_node_id, messages)

        if trigger_type == "once":
            if not run_at_str:
                logger.warning(f"Scheduled Event '{name}' has trigger_type 'once' but no run_at time")
                return
            try:
                run_at = datetime.fromisoformat(run_at_str)
                self.scheduler.schedule_once(
                    task_id=task_id,
                    agent_id=node.id,
                    callback=scheduled_tick,
                    run_at=run_at,
                )
                logger.info(f"Created one-time scheduled event '{name}' for {run_at}")
            except ValueError as e:
                logger.error(f"Invalid run_at datetime for '{name}': {e}")
        else:
            self.scheduler.schedule_interval(
                task_id=task_id,
                agent_id=node.id,
                callback=scheduled_tick,
                interval_seconds=interval_seconds,
                start_immediately=False,
            )
            logger.info(f"Created interval scheduled event '{name}' every {interval_seconds}s")

    def _stop_scheduled_event_node(self, node_id: str) -> None:
        """Stop a scheduled event node."""
        task_id = f"{node_id}_scheduled"
        self.scheduler.cancel_task(task_id)
        logger.info(f"Stopped scheduled event node: {node_id}")

    def _create_wait_and_combine_node(self, node: Node, agent_graph: AgentGraph) -> None:
        """Create a WaitAndCombine node that collects messages from multiple senders."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Wait and Combine")

        # Find all nodes that send to this node's message_in port
        expected_senders: set[str] = set()
        for edge in agent_graph.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.MESSAGE:
                continue
            if edge.target_node != node.id or edge.target_port != "message_in":
                continue
            expected_senders.add(edge.source_node)

        if not expected_senders:
            logger.warning(f"WaitAndCombine '{name}' ({node.id}) has no incoming connections")

        # Initialize state
        self.wait_and_combine_states[node.id] = WaitAndCombineState(
            expected_senders=expected_senders,
            senders_received=set(),
            pending_messages=[],
        )
        logger.info(f"Created WaitAndCombine node: {name} ({node.id}) expecting {len(expected_senders)} senders")

    def _deliver_to_wait_and_combine(
        self, 
        node_id: str, 
        sender_node_id: str, 
        messages: List[Dict[str, str]]
    ) -> None:
        """
        Deliver messages to a WaitAndCombine node.
        
        If all expected senders have sent, forwards combined messages to connected nodes.
        """
        state = self.wait_and_combine_states.get(node_id)
        if not state:
            logger.warning(f"WaitAndCombine state not found for node {node_id}")
            return

        # Add messages and mark sender as received
        state.pending_messages.extend(messages)
        state.senders_received.add(sender_node_id)

        node = self._current_agent_graph.get_node(node_id)
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Wait and Combine")

        logger.debug(
            f"WaitAndCombine '{name}': received from {sender_node_id}, "
            f"have {len(state.senders_received)}/{len(state.expected_senders)} senders"
        )

        # Check if all expected senders have sent
        if state.senders_received >= state.expected_senders:
            # All senders have sent - forward combined messages
            combined_messages = state.pending_messages.copy()
            
            # Reset state for next cycle
            state.senders_received.clear()
            state.pending_messages.clear()

            logger.info(
                f"WaitAndCombine '{name}': forwarding {len(combined_messages)} messages"
            )

            # Route combined messages to targets
            self._route_messages(node_id, name, combined_messages)

    # === Message Routing ===

    def _on_agent_message(self, event: Any) -> None:
        """Handle message events from agents (legacy event handler)."""
        pass  # No longer used - messages are routed via _route_messages

    def _on_agent_response(self, event: Any) -> None:
        """Handle response events from agents (legacy event handler)."""
        pass  # No longer used - messages are routed via _route_messages

    def _route_messages(
        self, 
        source_node_id: str, 
        source_name: str, 
        messages: List[Dict[str, str]]
    ) -> None:
        """
        Route messages through the graph to connected nodes.
        
        Args:
            source_node_id: ID of the node sending the messages
            source_name: Display name of the source (for logging/attribution)
            messages: List of message dicts with "sender" and "content" keys
        """
        if not self._current_agent_graph or not messages:
            return

        for edge in self._current_agent_graph.edges:
            if edge.source_node != source_node_id:
                continue
            if edge.source_port != "message_out":
                continue

            target_node = self._current_agent_graph.get_node(edge.target_node)
            if not target_node:
                continue

            if target_node.type == NodeType.USER_OUTPUT:
                # Send each message to user output
                if self.on_agent_graph_message:
                    for msg in messages:
                        self.on_agent_graph_message(source_node_id, msg["sender"], msg["content"])

            elif target_node.type == NodeType.AGENT:
                target_agent = self.agents.get(edge.target_node)
                if target_agent:
                    target_config = target_node.config if isinstance(target_node.config, dict) else target_node.config.model_dump()
                    target_name = target_config.get("name", "Agent")

                    logger.debug(f"Forwarding {len(messages)} message(s) from {source_name} to {target_name}")
                    response_messages = target_agent.process_message(messages)

                    if response_messages:
                        self._route_messages(edge.target_node, target_name, response_messages)

            elif target_node.type == NodeType.WAIT_AND_COMBINE:
                # Deliver to WaitAndCombine node
                self._deliver_to_wait_and_combine(edge.target_node, source_node_id, messages)

    def send_user_message(self, content: str, user: str = "User") -> list[dict]:
        """Send a message from user input to connected nodes (agents or WaitAndCombine)."""
        responses = []

        if not self._current_agent_graph:
            return responses

        # Find user input node
        user_input_node = None
        for node in self._current_agent_graph.nodes:
            if node.type == NodeType.USER_INPUT:
                user_input_node = node
                break

        # Create message in list format
        messages = [{"sender": user, "content": content}]

        if not user_input_node:
            # No user input node - send directly to all agents
            for agent_id in self.agents.keys():
                agent = self.agents.get(agent_id)
                if not agent:
                    continue

                agent_node = self._current_agent_graph.get_node(agent_id)
                agent_name = agent_node.config.name if agent_node else "Agent"

                response_messages = agent.process_message(messages)

                if response_messages:
                    responses.append({
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "response": response_messages[0]["content"],
                    })
                    self._route_messages(agent_id, agent_name, response_messages)
        else:
            # Route through user input node's connections
            for edge in self._current_agent_graph.edges:
                if edge.source_node != user_input_node.id:
                    continue
                if edge.edge_type != EdgeType.MESSAGE:
                    continue

                target_node = self._current_agent_graph.get_node(edge.target_node)
                if not target_node:
                    continue

                if target_node.type == NodeType.AGENT:
                    agent = self.agents.get(edge.target_node)
                    if agent:
                        agent_config = target_node.config if isinstance(target_node.config, dict) else target_node.config.model_dump()
                        agent_name = agent_config.get("name", "Agent")

                        response_messages = agent.process_message(messages)

                        if response_messages:
                            responses.append({
                                "agent_id": edge.target_node,
                                "agent_name": agent_name,
                                "response": response_messages[0]["content"],
                            })
                            self._route_messages(edge.target_node, agent_name, response_messages)

                elif target_node.type == NodeType.WAIT_AND_COMBINE:
                    # Deliver to WaitAndCombine node
                    self._deliver_to_wait_and_combine(edge.target_node, user_input_node.id, messages)

        return responses

    # === Persistence ===

    def persist_node_data(self, node_id: str) -> None:
        """Persist a node's data to disk."""
        if not self._current_agent_graph or not self._current_project_id:
            return

        node = self._current_agent_graph.get_node(node_id)
        if not node:
            return

        if node.type == NodeType.KNOWLEDGE_GRAPH:
            kg = self.knowledge_graphs.get(node_id)
            if kg is not None:
                self.storage.save_knowledge_graph(self._current_project_id, node_id, kg)
                logger.debug(f"Persisted KG node {node_id} with {len(kg)} entities")
            else:
                logger.warning(f"Knowledge graph node {node_id} not found in runtime")

        elif node.type == NodeType.MEMORY_STREAM:
            ms = self.memory_streams.get(node_id)
            if ms is not None:
                self.storage.save_memory_stream(self._current_project_id, node_id, ms)

    def persist_all(self) -> None:
        """Persist all node data."""
        if not self._current_agent_graph:
            return

        for node in self._current_agent_graph.nodes:
            self.persist_node_data(node.id)

    # === Query Methods ===

    def get_running_agents(self) -> list[dict]:
        """Get list of running agents."""
        if not self.is_deployed or not self._current_agent_graph:
            return []

        agents = []
        for node in self._current_agent_graph.nodes:
            if node.type == NodeType.AGENT and node.id in self.agents:
                config = node.config if isinstance(node.config, dict) else node.config.model_dump()
                agents.append({
                    "id": node.id,
                    "name": config.get("name", "Agent"),
                    "state": "running",
                })
        return agents

