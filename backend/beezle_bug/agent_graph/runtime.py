"""
AgentGraphRuntime - manages the runtime state of a deployed agent graph.

Responsibilities:
- Deploy/undeploy agent graphs
- Manage live agent, KG, memory stream instances
- Route messages between connected nodes
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable
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
            response = target_agent.process_message(source_name, self.question)
            return response if response else "No response from agent"
    
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
        """Start a Scheduled Event node that sends messages to connected agents."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Scheduled Event")
        trigger_type = config.get("trigger_type", "interval")
        run_at_str = config.get("run_at")
        interval_seconds = config.get("interval_seconds", 30)
        message_content = config.get("message_content", "Review your current state and pending tasks.")

        # Find connected agents via MESSAGE edges from message_out port
        target_agent_ids = []
        for edge in agent_graph.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.MESSAGE:
                continue
            if edge.source_node != node.id or edge.source_port != "message_out":
                continue
            target_node = agent_graph.get_node(edge.target_node)
            if target_node and target_node.type == NodeType.AGENT:
                target_agent_ids.append(edge.target_node)

        if not target_agent_ids:
            logger.warning(f"Scheduled Event '{name}' ({node.id}) has no connected agents")
            return

        task_id = f"{node.id}_scheduled"

        def scheduled_tick(agent_ids=target_agent_ids, event_name=name, content=message_content):
            for agent_id in agent_ids:
                agent = self.agents.get(agent_id)
                if agent:
                    agent_node = agent_graph.get_node(agent_id)
                    agent_name = "Agent"
                    if agent_node:
                        agent_config = agent_node.config if isinstance(agent_node.config, dict) else agent_node.config.model_dump()
                        agent_name = agent_config.get("name", "Agent")

                    response = agent.process_message(event_name, content)
                    if response:
                        self._route_agent_response(agent_id, agent_name, response)

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

    # === Message Routing ===

    def _on_agent_message(self, event: Any) -> None:
        """Handle message events from agents."""
        if not self._current_agent_graph:
            return

        source_agent_id = event.data.get("agent_id")
        if not source_agent_id:
            return

        for edge in self._current_agent_graph.edges:
            if edge.source_node != source_agent_id:
                continue
            if edge.edge_type not in (EdgeType.MESSAGE, EdgeType.PIPELINE):
                continue

            target_agent = self.agents.get(edge.target_node)
            if target_agent:
                logger.debug(f"Routing message {source_agent_id} -> {edge.target_node}")
                target_agent.receive_message(event.data.get("content", ""))

    def _on_agent_response(self, event: Any) -> None:
        """Handle response events from agents."""
        pass

    def _route_agent_response(self, agent_id: str, agent_name: str, response: str) -> None:
        """Route an agent's response through the graph to connected nodes."""
        if not self._current_agent_graph:
            return

        for edge in self._current_agent_graph.edges:
            if edge.source_node != agent_id:
                continue
            if edge.source_port != "message_out":
                continue

            target_node = self._current_agent_graph.get_node(edge.target_node)
            if not target_node:
                continue

            if target_node.type == NodeType.USER_OUTPUT:
                if self.on_agent_graph_message:
                    self.on_agent_graph_message(agent_id, agent_name, response)
            elif target_node.type == NodeType.AGENT:
                target_agent = self.agents.get(edge.target_node)
                if target_agent:
                    target_config = target_node.config if isinstance(target_node.config, dict) else target_node.config.model_dump()
                    target_name = target_config.get("name", "Agent")

                    logger.debug(f"Forwarding message from {agent_name} to {target_name}")
                    target_response = target_agent.process_message(agent_name, response)

                    if target_response:
                        self._route_agent_response(edge.target_node, target_name, target_response)

    def send_user_message(self, content: str, user: str = "User") -> list[dict]:
        """Send a message from user input to connected agents."""
        responses = []

        if not self._current_agent_graph:
            return responses

        # Find user input node
        user_input_node = None
        for node in self._current_agent_graph.nodes:
            if node.type == NodeType.USER_INPUT:
                user_input_node = node
                break

        # Get target agents
        target_agent_ids = []

        if not user_input_node:
            target_agent_ids = list(self.agents.keys())
        else:
            for edge in self._current_agent_graph.edges:
                if edge.source_node != user_input_node.id:
                    continue
                if edge.edge_type != EdgeType.MESSAGE:
                    continue
                if edge.target_node in self.agents:
                    target_agent_ids.append(edge.target_node)

        # Process message with each target agent
        for agent_id in target_agent_ids:
            agent = self.agents.get(agent_id)
            if not agent:
                continue

            agent_node = self._current_agent_graph.get_node(agent_id)
            agent_name = agent_node.config.name if agent_node else "Agent"

            response = agent.process_message(user, content)

            if response:
                responses.append({
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "response": response,
                })
                self._route_agent_response(agent_id, agent_name, response)

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

