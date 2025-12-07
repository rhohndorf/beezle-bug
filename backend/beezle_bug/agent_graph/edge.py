"""
Edge class for the Agent Graph system.
"""

import uuid
from pydantic import BaseModel, Field

from .types import EdgeType


class Edge(BaseModel):
    """A connection between two nodes in the agent graph."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_node: str  # Node ID
    source_port: str  # Port name
    target_node: str  # Node ID
    target_port: str  # Port name
    edge_type: EdgeType

