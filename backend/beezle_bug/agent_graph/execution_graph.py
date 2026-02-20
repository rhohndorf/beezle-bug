"""
Execution Graph - the runtime representation of an agent graph.

The ExecutionGraph is built from the design-time AgentGraph and contains
only the elements needed for execution:
- Executable nodes (agents, future logic nodes)
- Message buffers (collect messages until triggered)
- Pre-computed routing table
- Entry and exit point information
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .executable import Executable
    from beezle_bug.memory.knowledge_graph import KnowledgeGraph


@dataclass
class ScheduledEventConfig:
    """Configuration for a scheduled event."""
    node_id: str
    name: str
    trigger_type: str  # "interval" or "once"
    interval_seconds: int
    run_at: Optional[datetime]
    message_content: str


@dataclass
class MessageBufferState:
    """Runtime state for a MessageBuffer.
    
    Collects messages on the message_in port until triggered,
    then flushes all buffered messages on the message_out port.
    """
    pending_messages: list[dict] = field(default_factory=list)
    
    def buffer(self, messages: list[dict]) -> None:
        """Add messages to the buffer."""
        self.pending_messages.extend(messages)
    
    def flush(self) -> list[dict]:
        """Get buffered messages and clear the buffer."""
        msgs = self.pending_messages.copy()
        self.pending_messages.clear()
        return msgs


@dataclass
class ExecutionGraph:
    """
    The runtime representation of an agent graph.
    
    Built from the design-time AgentGraph by ExecutionGraphBuilder.
    Contains only what's needed for execution - no UI/persistence concerns.
    """
    # Message processors (Agent instances, future logic nodes)
    # All implement the Executable protocol
    executables: dict[str, "Executable"] = field(default_factory=dict)
    
    # Message buffers - collect messages until triggered
    message_buffers: dict[str, MessageBufferState] = field(default_factory=dict)
    
    # Entry points - where messages can originate
    # Event node IDs (for walking the graph from these nodes)
    text_input_event_ids: list[str] = field(default_factory=list)
    voice_input_event_ids: list[str] = field(default_factory=list)
    # Executable IDs that receive messages from event nodes (for direct execution)
    text_entry_ids: list[str] = field(default_factory=list)
    voice_entry_ids: list[str] = field(default_factory=list)
    scheduled_events: list[ScheduledEventConfig] = field(default_factory=list)
    
    # Routing table: source_id -> [(target_type, target_id), ...]
    # target_type is "executable", "message_buffer_in", "message_buffer_trigger", or "exit"
    routing: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    
    # Exit points - executable IDs whose output should be delivered to user
    exit_ids: set[str] = field(default_factory=set)
    
    # Resources - kept for introspection/debugging endpoints
    knowledge_graphs: dict[str, "KnowledgeGraph"] = field(default_factory=dict)
