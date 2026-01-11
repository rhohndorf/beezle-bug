"""
ExecutionGraphBuilder - transforms a design-time AgentGraph into an ExecutionGraph.

This builder handles:
- Loading resources (KG, MemoryStream) from storage
- Building toolboxes from tool names
- Creating Agent instances with resources injected
- Setting up delegate tools for agent-to-agent communication
- Computing entry points, routing table, and exit points
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from loguru import logger

from .types import NodeType, EdgeType
from .node import Node
from .agent_graph import AgentGraph
from .agent import Agent
from .execution_graph import (
    ExecutionGraph,
    ScheduledEventConfig,
    MessageBufferState,
)

from beezle_bug.memory.knowledge_graph import KnowledgeGraph
from beezle_bug.memory.memory_stream import MemoryStream
from beezle_bug.events import EventBus
from beezle_bug.template import TemplateLoader
from beezle_bug.tools.toolbox_factory import ToolboxFactory
from beezle_bug.tools import Tool
from beezle_bug.llm_adapter import OpenAiAdapter

if TYPE_CHECKING:
    from beezle_bug.storage.base import StorageBackend


def create_delegate_tool(
    executables: dict,
    target_node_id: str,
    target_name: str,
    source_name: str
) -> type[Tool]:
    """
    Create a delegate tool class that calls another agent.
    
    Args:
        executables: Reference to the execution graph's executables dict
        target_node_id: The node ID of the target agent
        target_name: The display name of the target agent
        source_name: The name of the calling agent (for attribution)
    
    Returns:
        A Tool class that, when called, asks the target agent a question
    """
    safe_name = target_name.lower().replace(' ', '_').replace('-', '_')
    tool_name = f"ask_{safe_name}"
    
    class DelegateTool(Tool):
        question: str
        
        async def run(self, agent) -> str:
            target_agent = executables.get(target_node_id)
            if not target_agent:
                return f"Error: Agent '{target_name}' is not available"
            messages = [{"sender": source_name, "content": self.question}]
            response_messages = await target_agent.execute(messages)
            if response_messages:
                return response_messages[0]["content"]
            return "No response from agent"
    
    DelegateTool.__name__ = tool_name
    DelegateTool.__doc__ = f"Ask {target_name} a question and get their response. Use this when you need {target_name}'s expertise or input."
    
    return DelegateTool


class ExecutionGraphBuilder:
    """
    Builds an ExecutionGraph from a design-time AgentGraph.
    
    The builder loads resources from storage, creates agent instances,
    and computes the routing table and entry/exit points.
    """
    
    def __init__(
        self,
        storage: "StorageBackend",
        event_bus: EventBus,
        template_loader: TemplateLoader,
        toolbox_factory: ToolboxFactory,
    ):
        self.storage = storage
        self.event_bus = event_bus
        self.template_loader = template_loader
        self.toolbox_factory = toolbox_factory
    
    async def build(self, design: AgentGraph, project_id: str) -> ExecutionGraph:
        """
        Transform a design-time AgentGraph into an ExecutionGraph.
        
        Args:
            design: The design-time agent graph from UI/persistence
            project_id: The project ID for storage operations
            
        Returns:
            An ExecutionGraph ready for runtime execution
        """
        logger.info(f"Building execution graph for project {project_id}")
        
        # 1. Load resources (not nodes - just objects)
        kgs = await self._load_knowledge_graphs(design, project_id)
        memory_streams = await self._load_memory_streams(design, project_id)
        toolboxes = self._build_toolboxes(design)
        
        # 2. Build executables dict (will be populated with agents)
        executables: dict = {}
        
        # 3. Build agents with resources injected
        for node in design.nodes:
            if node.type == NodeType.AGENT:
                agent = await self._build_agent(
                    node, design, project_id,
                    kgs, memory_streams, toolboxes,
                    executables  # Pass for delegate tools
                )
                executables[node.id] = agent
        
        # 4. Build MessageBuffer states
        message_buffers = {}
        for node in design.nodes:
            if node.type == NodeType.MESSAGE_BUFFER:
                state = self._build_message_buffer(node)
                message_buffers[node.id] = state
        
        # 5. Identify entry points
        # Find event node IDs
        text_input_event_ids = [n.id for n in design.nodes if n.type == NodeType.TEXT_INPUT_EVENT]
        voice_input_event_ids = [n.id for n in design.nodes if n.type == NodeType.VOICE_INPUT_EVENT]
        # Find executable targets of event nodes
        text_entry_ids = self._find_targets_of(NodeType.TEXT_INPUT_EVENT, design)
        voice_entry_ids = self._find_targets_of(NodeType.VOICE_INPUT_EVENT, design)
        scheduled_events = self._build_scheduled_configs(design)
        
        # 6. Build routing table
        routing = self._build_routing_table(design, executables, message_buffers)
        
        # 7. Identify exits
        exit_ids = self._find_sources_of(NodeType.TEXT_OUTPUT, design)
        
        logger.info(
            f"Built execution graph: {len(executables)} executables, "
            f"{len(message_buffers)} message_buffers, "
            f"{len(text_entry_ids)} text entries, {len(voice_entry_ids)} voice entries, "
            f"{len(scheduled_events)} scheduled events, {len(exit_ids)} exits"
        )
        
        return ExecutionGraph(
            executables=executables,
            message_buffers=message_buffers,
            text_input_event_ids=text_input_event_ids,
            voice_input_event_ids=voice_input_event_ids,
            text_entry_ids=text_entry_ids,
            voice_entry_ids=voice_entry_ids,
            scheduled_events=scheduled_events,
            routing=routing,
            exit_ids=exit_ids,
            knowledge_graphs=kgs,
        )
    
    async def _load_knowledge_graphs(
        self, design: AgentGraph, project_id: str
    ) -> dict[str, KnowledgeGraph]:
        """Load KnowledgeGraph instances for all KG nodes."""
        kgs = {}
        for node in design.nodes:
            if node.type == NodeType.KNOWLEDGE_GRAPH:
                config = node.config if isinstance(node.config, dict) else node.config.model_dump()
                name = config.get("name", "Knowledge Graph")
                
                # Ensure KG exists in database
                kg_id = await self.storage.kg_ensure(project_id, node.id)
                
                # Load existing data
                kg = await self.storage.kg_load_full(project_id, node.id)
                if kg is None:
                    kg = KnowledgeGraph(storage=self.storage, kg_id=kg_id)
                else:
                    kg._storage = self.storage
                    kg._kg_id = kg_id
                
                kgs[node.id] = kg
                logger.info(f"Loaded KG: {name} ({node.id}), db_id={kg_id}")
        
        return kgs
    
    async def _load_memory_streams(
        self, design: AgentGraph, project_id: str
    ) -> dict[str, MemoryStream]:
        """Load MemoryStream instances for all MS nodes."""
        memory_streams = {}
        for node in design.nodes:
            if node.type == NodeType.MEMORY_STREAM:
                config = node.config if isinstance(node.config, dict) else node.config.model_dump()
                name = config.get("name", "Memory Stream")
                
                # Ensure MS exists in database
                ms_id = await self.storage.ms_ensure(project_id, node.id)
                
                # Create storage-aware memory stream
                ms = MemoryStream(storage=self.storage, ms_id=ms_id)
                
                # Load metadata
                metadata = await self.storage.ms_get_metadata(ms_id)
                ms.last_reflection_point = metadata.get("last_reflection_point", 0)
                
                memory_streams[node.id] = ms
                logger.info(f"Loaded MemoryStream: {name} ({node.id}), db_id={ms_id}")
        
        return memory_streams
    
    def _build_toolboxes(self, design: AgentGraph) -> dict[str, list[str]]:
        """Build toolbox configs (tool name lists) for all Toolbox nodes."""
        toolboxes = {}
        for node in design.nodes:
            if node.type == NodeType.TOOLBOX:
                config = node.config if isinstance(node.config, dict) else node.config.model_dump()
                name = config.get("name", "Toolbox")
                tools = config.get("tools", [])
                toolboxes[node.id] = tools
                logger.info(f"Built Toolbox: {name} ({node.id}) with {len(tools)} tools")
        
        return toolboxes
    
    async def _build_agent(
        self,
        node: Node,
        design: AgentGraph,
        project_id: str,
        kgs: dict[str, KnowledgeGraph],
        memory_streams: dict[str, MemoryStream],
        toolboxes: dict[str, list[str]],
        executables: dict,
    ) -> Agent:
        """Build an Agent instance with resources injected."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        
        # Find connected resources via RESOURCE edges
        kg = None
        memory_stream = None
        tools = []
        
        for edge in design.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.RESOURCE:
                continue
            
            resource_node_id = (
                edge.target_node if edge.source_node == node.id else edge.source_node
            )
            resource_node = design.get_node(resource_node_id)
            
            if resource_node and resource_node.type == NodeType.KNOWLEDGE_GRAPH:
                kg = kgs.get(resource_node_id)
            elif resource_node and resource_node.type == NodeType.MEMORY_STREAM:
                memory_stream = memory_streams.get(resource_node_id)
            elif resource_node and resource_node.type == NodeType.TOOLBOX:
                toolbox_tools = toolboxes.get(resource_node_id, [])
                tools.extend(toolbox_tools)
        
        # Extract config values
        name = config.get("name", "Agent")
        model = config.get("model", "gpt-4")
        api_url = config.get("api_url", "http://127.0.0.1:1234/v1")
        api_key = config.get("api_key", "")
        system_template_name = config.get("system_template", "agent")
        context_size = config.get("context_size", 25)
        
        # Create toolbox from tool names
        toolbox = self.toolbox_factory(tools)
        
        # Find DELEGATE edges and create delegate tools
        for edge in design.get_edges_for_node(node.id):
            if edge.edge_type != EdgeType.DELEGATE:
                continue
            if edge.source_node != node.id or edge.source_port != "ask":
                continue
            
            target_node = design.get_node(edge.target_node)
            if target_node and target_node.type == NodeType.AGENT:
                target_config = target_node.config if isinstance(target_node.config, dict) else target_node.config.model_dump()
                target_name = target_config.get("name", "Agent")
                
                delegate_tool = create_delegate_tool(
                    executables=executables,
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
            system_template=template,
            event_bus=self.event_bus,
            memory_stream=memory_stream,
            knowledge_graph=kg if kg is not None else KnowledgeGraph(),
            context_size=context_size,
        )
        
        logger.info(f"Built Agent: {name} ({node.id})")
        return agent
    
    def _build_message_buffer(self, node: Node) -> MessageBufferState:
        """Build MessageBuffer state for a node."""
        config = node.config if isinstance(node.config, dict) else node.config.model_dump()
        name = config.get("name", "Message Buffer")
        
        logger.info(f"Built MessageBuffer: {name} ({node.id})")
        
        return MessageBufferState()
    
    def _find_targets_of(self, node_type: NodeType, design: AgentGraph) -> list[str]:
        """Find executable IDs that are direct MESSAGE targets of a node type."""
        targets = []
        for node in design.nodes:
            if node.type == node_type:
                for edge in design.edges:
                    if edge.source_node == node.id and edge.edge_type == EdgeType.MESSAGE:
                        targets.append(edge.target_node)
        return targets
    
    def _find_sources_of(self, node_type: NodeType, design: AgentGraph) -> set[str]:
        """Find executable IDs that send MESSAGE edges to a node type."""
        sources = set()
        for node in design.nodes:
            if node.type == node_type:
                for edge in design.edges:
                    if edge.target_node == node.id and edge.edge_type == EdgeType.MESSAGE:
                        sources.add(edge.source_node)
        return sources
    
    def _build_scheduled_configs(self, design: AgentGraph) -> list[ScheduledEventConfig]:
        """Build ScheduledEventConfig for all scheduled event nodes."""
        configs = []
        for node in design.nodes:
            if node.type == NodeType.SCHEDULED_EVENT:
                config = node.config if isinstance(node.config, dict) else node.config.model_dump()
                
                run_at = None
                run_at_str = config.get("run_at")
                if run_at_str:
                    try:
                        run_at = datetime.fromisoformat(run_at_str)
                    except ValueError:
                        pass
                
                configs.append(ScheduledEventConfig(
                    node_id=node.id,
                    name=config.get("name", "Scheduled Event"),
                    trigger_type=config.get("trigger_type", "interval"),
                    interval_seconds=config.get("interval_seconds", 30),
                    run_at=run_at,
                    message_content=config.get("message_content", "Review your current state and pending tasks."),
                ))
        
        return configs
    
    def _build_routing_table(
        self,
        design: AgentGraph,
        executables: dict,
        message_buffers: dict[str, MessageBufferState],
    ) -> dict[str, list[tuple[str, str]]]:
        """
        Build the routing table from MESSAGE edges.
        
        Returns a dict mapping source_id to list of (target_type, target_id) tuples.
        target_type is one of: "executable", "message_buffer_in", "message_buffer_trigger", "exit"
        """
        routing: dict[str, list[tuple[str, str]]] = {}
        
        for edge in design.edges:
            if edge.edge_type != EdgeType.MESSAGE:
                continue
            if edge.source_port != "message_out":
                continue
            
            source_id = edge.source_node
            target_id = edge.target_node
            target_node = design.get_node(target_id)
            
            if not target_node:
                continue
            
            # Determine target type
            if target_id in executables:
                target_type = "executable"
            elif target_id in message_buffers:
                # Distinguish between message_in and trigger ports
                if edge.target_port == "trigger":
                    target_type = "message_buffer_trigger"
                else:
                    target_type = "message_buffer_in"
            elif target_node.type == NodeType.TEXT_OUTPUT:
                target_type = "exit"
            else:
                # Skip non-routable targets
                continue
            
            if source_id not in routing:
                routing[source_id] = []
            routing[source_id].append((target_type, target_id))
        
        return routing
