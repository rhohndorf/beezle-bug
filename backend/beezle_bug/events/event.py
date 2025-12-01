from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class EventType(Enum):
    """Enumeration of all possible event types emitted by agents."""
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    LLM_CALL_STARTED = "llm.call.started"
    LLM_CALL_COMPLETED = "llm.call.completed"
    TOOL_SELECTED = "tool.selected"
    TOOL_COMPLETED = "tool.execution.completed"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class Event:
    """Represents a single event in the system."""
    type: EventType
    agent_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'type': self.type.value,
            'agent_name': self.agent_name,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data
        }