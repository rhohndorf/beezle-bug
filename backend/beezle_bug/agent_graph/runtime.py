"""
AgentGraphRuntime - manages the runtime state of a deployed agent graph.

Responsibilities:
- Deploy/undeploy agent graphs using ExecutionGraphBuilder
- Route messages through the execution graph
- Handle scheduled events

All message processing and storage operations are async.
"""

from typing import TYPE_CHECKING, Optional, Callable, List, Dict
from loguru import logger

from .types import NodeType
from .agent_graph import AgentGraph
from .execution_graph import ExecutionGraph
from .execution_graph_builder import ExecutionGraphBuilder

from beezle_bug.events import EventBus, EventType
from beezle_bug.scheduler import Scheduler
from beezle_bug.template import TemplateLoader
from beezle_bug.tools.toolbox_factory import ToolboxFactory

if TYPE_CHECKING:
    from beezle_bug.storage.base import StorageBackend


class AgentGraphRuntime:
    """
    Manages the runtime state of a deployed agent graph.
    
    Uses ExecutionGraphBuilder to transform the design-time AgentGraph
    into an ExecutionGraph, then executes message flow using the
    pre-computed routing table.
    """

    def __init__(
        self,
        storage: "StorageBackend",
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

        # Builder for transforming design graph to execution graph
        self.builder = ExecutionGraphBuilder(
            storage=storage,
            event_bus=event_bus,
            template_loader=template_loader,
            toolbox_factory=toolbox_factory,
        )

        # Deployment state
        self.is_deployed: bool = False
        self._current_project_id: Optional[str] = None
        self._current_design: Optional[AgentGraph] = None  # Keep for get_running_agents
        self.exec_graph: Optional[ExecutionGraph] = None

        # Subscribe to events (for introspection, not routing)
        self.event_bus.subscribe(EventType.MESSAGE_SENT, self._on_agent_message)
        self.event_bus.subscribe(EventType.MESSAGE_RECEIVED, self._on_agent_response)

    # === Deploy / Undeploy ===

    async def deploy(self, agent_graph: AgentGraph, project_id: str) -> None:
        """Deploy an agent graph - build execution graph and start scheduled events."""
        if self.is_deployed:
            logger.warning("Already deployed, undeploying first")
            await self.undeploy()

        self._current_project_id = project_id
        self._current_design = agent_graph

        logger.info(f"Deploying agent graph for project {project_id}")
        
        # Build execution graph from design graph
        self.exec_graph = await self.builder.build(agent_graph, project_id)
        
        # Start scheduled events
        self._start_scheduled_events()
        
        self.is_deployed = True
        logger.info(f"Agent graph deployed for project {project_id}")

    async def undeploy(self) -> None:
        """Undeploy - stop scheduled events and clear execution graph."""
        if not self.is_deployed or not self.exec_graph:
            return

        logger.info("Undeploying agent graph")

        # Stop all scheduled events
        self._stop_scheduled_events()

        # Clear execution graph
        self.exec_graph = None
        self._current_design = None
        self._current_project_id = None
        self.is_deployed = False
        
        logger.info("Agent graph undeployed")

    # === Scheduled Events ===

    def _start_scheduled_events(self) -> None:
        """Start all scheduled events in the execution graph."""
        if not self.exec_graph:
            return
            
        for config in self.exec_graph.scheduled_events:
            task_id = f"{config.node_id}_scheduled"
            
            # Check if this scheduled event has any routing targets
            if config.node_id not in self.exec_graph.routing:
                logger.warning(
                    f"Scheduled Event '{config.name}' ({config.node_id}) has no connected targets"
                )
                continue
            
            # Create callback that walks graph from scheduled event
            async def on_tick(cfg=config):
                messages = [{"sender": cfg.name, "content": cfg.message_content}]
                await self._walk_graph_from_scheduled(cfg.node_id, messages)
            
            if config.trigger_type == "once" and config.run_at:
                self.scheduler.schedule_once(
                    task_id=task_id,
                    agent_id=config.node_id,
                    callback=on_tick,
                    run_at=config.run_at,
                )
                logger.info(f"Scheduled one-time event '{config.name}' for {config.run_at}")
            else:
                self.scheduler.schedule_interval(
                    task_id=task_id,
                    agent_id=config.node_id,
                    callback=on_tick,
                    interval_seconds=config.interval_seconds,
                    start_immediately=False,
                )
                logger.info(f"Scheduled interval event '{config.name}' every {config.interval_seconds}s")

    def _stop_scheduled_events(self) -> None:
        """Stop all scheduled events."""
        if not self.exec_graph:
            return
            
        for config in self.exec_graph.scheduled_events:
            task_id = f"{config.node_id}_scheduled"
            self.scheduler.cancel_task(task_id)
            logger.info(f"Stopped scheduled event: {config.name}")

    async def _walk_graph_from_scheduled(self, node_id: str, messages: List[Dict[str, str]]) -> None:
        """Walk graph starting from a scheduled event node."""
        if not self.exec_graph:
            return
        await self._walk_graph(node_id, messages)

    # === Graph Walking ===

    async def _walk_graph(self, source_id: str, messages: List[Dict[str, str]]) -> None:
        """
        Walk graph from source, routing messages to targets using routing table.
        
        Args:
            source_id: ID of the source node
            messages: Messages to route
        """
        if not self.exec_graph or not messages:
            return

        for target_type, target_id in self.exec_graph.routing.get(source_id, []):
            if target_type == "executable":
                node = self.exec_graph.executables.get(target_id)
                if node:
                    logger.debug(f"Routing {len(messages)} message(s) to {node.name}")
                    outputs = await node.execute(messages)
                    if outputs:
                        # Deliver to user if this is an exit node
                        if target_id in self.exec_graph.exit_ids:
                            self._deliver_to_user(node.name, outputs)
                        # Continue walking
                        await self._walk_graph(target_id, outputs)
            
            elif target_type == "message_buffer_in":
                # Buffer messages (will be released when triggered)
                state = self.exec_graph.message_buffers.get(target_id)
                if state:
                    state.buffer(messages)
                    logger.debug(f"MessageBuffer {target_id}: buffered {len(messages)} message(s)")
            
            elif target_type == "message_buffer_trigger":
                # Trigger flushes the buffer and sends messages downstream
                state = self.exec_graph.message_buffers.get(target_id)
                if state:
                    buffered = state.flush()
                    logger.info(f"MessageBuffer {target_id}: triggered, flushing {len(buffered)} message(s)")
                    if buffered:
                        await self._walk_graph(target_id, buffered)
            
            # Note: "exit" target type is not handled here because
            # executables connected to TextOutput are in exit_ids and
            # delivery happens in _execute_and_route()

    def _deliver_to_user(self, sender_name: str, messages: List[Dict[str, str]]) -> None:
        """Deliver messages to user via callback."""
        if self.on_agent_graph_message:
            for msg in messages:
                self.on_agent_graph_message("", msg["sender"], msg["content"])

    # === Entry Points ===

    async def _execute_and_route(self, agent_id: str, messages: List[Dict[str, str]]) -> Optional[Dict]:
        """Execute an agent and route its output, returning response info."""
        if not self.exec_graph:
            return None
            
        agent = self.exec_graph.executables.get(agent_id)
        if not agent:
            return None
        
        outputs = await agent.execute(messages)
        if outputs:
            # Deliver to user if this is an exit node
            if agent_id in self.exec_graph.exit_ids:
                self._deliver_to_user(agent.name, outputs)
            # Continue walking
            await self._walk_graph(agent_id, outputs)
            return {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "response": outputs[0]["content"],
            }
        return None

    async def send_user_message(self, content: str, user: str = "User") -> list[dict]:
        """Send a message from text input to connected agents."""
        responses = []
        
        if not self.exec_graph:
            return responses

        messages = [{"sender": user, "content": content}]

        if self.exec_graph.text_input_event_ids:
            # First, deliver to MessageBuffer targets from event nodes
            for event_id in self.exec_graph.text_input_event_ids:
                for target_type, target_id in self.exec_graph.routing.get(event_id, []):
                    if target_type == "message_buffer_in":
                        state = self.exec_graph.message_buffers.get(target_id)
                        if state:
                            state.buffer(messages)
                            logger.debug(f"MessageBuffer {target_id}: buffered {len(messages)} message(s) from text input")
                    elif target_type == "message_buffer_trigger":
                        state = self.exec_graph.message_buffers.get(target_id)
                        if state:
                            buffered = state.flush()
                            logger.info(f"MessageBuffer {target_id}: triggered by text input, flushing {len(buffered)} message(s)")
                            if buffered:
                                await self._walk_graph(target_id, buffered)
            
            # Then execute connected agents (executables are handled separately to collect responses)
            for agent_id in self.exec_graph.text_entry_ids:
                result = await self._execute_and_route(agent_id, messages)
                if result:
                    responses.append(result)
        else:
            # No text input node - send to all executables (fallback)
            for agent_id in self.exec_graph.executables.keys():
                result = await self._execute_and_route(agent_id, messages)
                if result:
                    responses.append(result)

        return responses

    async def send_voice_message(self, content: str, user: str = "User") -> list[dict]:
        """Send a voice-transcribed message to connected agents."""
        responses = []
        
        if not self.exec_graph:
            return responses

        messages = [{"sender": user, "content": content}]

        if self.exec_graph.voice_input_event_ids:
            # First, deliver to MessageBuffer targets from event nodes
            for event_id in self.exec_graph.voice_input_event_ids:
                for target_type, target_id in self.exec_graph.routing.get(event_id, []):
                    if target_type == "message_buffer_in":
                        state = self.exec_graph.message_buffers.get(target_id)
                        if state:
                            state.buffer(messages)
                            logger.debug(f"MessageBuffer {target_id}: buffered {len(messages)} message(s) from voice input")
                    elif target_type == "message_buffer_trigger":
                        state = self.exec_graph.message_buffers.get(target_id)
                        if state:
                            buffered = state.flush()
                            logger.info(f"MessageBuffer {target_id}: triggered by voice input, flushing {len(buffered)} message(s)")
                            if buffered:
                                await self._walk_graph(target_id, buffered)
            
            # Then execute connected agents
            for agent_id in self.exec_graph.voice_entry_ids:
                result = await self._execute_and_route(agent_id, messages)
                if result:
                    responses.append(result)
        else:
            # No voice input node - fallback to text entry behavior
            return await self.send_user_message(content, user)

        return responses

    # === Event Handlers (for introspection) ===

    def _on_agent_message(self, event) -> None:
        """Handle message events from agents (for introspection)."""
        pass

    def _on_agent_response(self, event) -> None:
        """Handle response events from agents (for introspection)."""
        pass

    # === Query Methods ===

    def get_running_agents(self) -> list[dict]:
        """Get list of running agents."""
        if not self.is_deployed or not self.exec_graph:
            return []

        agents = []
        for agent_id, agent in self.exec_graph.executables.items():
            agents.append({
                "id": agent_id,
                "name": agent.name,
                "state": "running",
            })
        return agents
