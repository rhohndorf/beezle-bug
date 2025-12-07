"""
Type definitions for the Agent Graph system.

Contains enums, position, and node configuration classes.
"""

from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes that can exist in an agent graph."""
    AGENT = "agent"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    MEMORY_STREAM = "memory_stream"
    TOOLBOX = "toolbox"
    USER_INPUT = "user_input"
    USER_OUTPUT = "user_output"
    SCHEDULED_EVENT = "scheduled_event"


class EdgeType(str, Enum):
    """Types of edges/connections between nodes."""
    MESSAGE = "message"      # Direct message passing between agents or event nodes
    PIPELINE = "pipeline"    # Output becomes input (chained processing)
    RESOURCE = "resource"    # Bidirectional read/write access to KG/Memory
    DELEGATE = "delegate"    # Sync call: agent A asks agent B, gets response as tool result


class Position(BaseModel):
    """2D position of a node in the graph UI."""
    x: float = 0.0
    y: float = 0.0


# Node Configuration Types

class AgentNodeConfig(BaseModel):
    """Configuration for an Agent node."""
    name: str
    model: str = "gpt-4"
    api_url: str = "http://127.0.0.1:1234/v1"
    api_key: str = ""
    system_template: str = "agent"


class KnowledgeGraphNodeConfig(BaseModel):
    """Configuration for a Knowledge Graph node."""
    name: str = "Knowledge Graph"


class MemoryStreamNodeConfig(BaseModel):
    """Configuration for a Memory Stream node."""
    name: str = "Memory Stream"
    max_observations: int = 1000


class ToolboxNodeConfig(BaseModel):
    """Configuration for a Toolbox node."""
    name: str = "Toolbox"
    tools: list[str] = Field(default_factory=list)


class UserInputNodeConfig(BaseModel):
    """Configuration for User Input node (chat entry point)."""
    name: str = "User Chat"


class UserOutputNodeConfig(BaseModel):
    """Configuration for User Output node (chat display)."""
    name: str = "User Display"


class ScheduledEventNodeConfig(BaseModel):
    """Configuration for a Scheduled Event node."""
    name: str = "Scheduled Event"
    trigger_type: str = "interval"  # "once" or "interval"
    run_at: Optional[str] = None    # ISO datetime for "once"
    interval_seconds: int = 30       # For "interval"
    message_content: str = "Review your current state and pending tasks."


# Union type for all node configs
NodeConfig = Union[
    AgentNodeConfig,
    KnowledgeGraphNodeConfig,
    MemoryStreamNodeConfig,
    ToolboxNodeConfig,
    UserInputNodeConfig,
    UserOutputNodeConfig,
    ScheduledEventNodeConfig,
]

