"""
Node class for the Agent Graph system.
"""

import uuid
from pydantic import BaseModel, Field

from .types import NodeType, Position, NodeConfig


class Node(BaseModel):
    """A node in the agent graph."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    type: NodeType
    position: Position = Field(default_factory=Position)
    config: NodeConfig

    def get_ports(self) -> dict[str, list[str]]:
        """Get available ports for this node type."""
        if self.type == NodeType.AGENT:
            return {
                "inputs": ["message_in", "answer"],
                "outputs": ["message_out", "ask"],
                "bidirectional": ["knowledge", "memory", "tools"],
            }
        elif self.type == NodeType.KNOWLEDGE_GRAPH:
            return {
                "inputs": [],
                "outputs": [],
                "bidirectional": ["connection"],
            }
        elif self.type == NodeType.MEMORY_STREAM:
            return {
                "inputs": [],
                "outputs": [],
                "bidirectional": ["connection"],
            }
        elif self.type == NodeType.TOOLBOX:
            return {
                "inputs": [],
                "outputs": [],
                "bidirectional": ["connection"],
            }
        elif self.type == NodeType.TEXT_INPUT_EVENT:
            return {
                "inputs": [],
                "outputs": ["message_out"],
                "bidirectional": [],
            }
        elif self.type == NodeType.VOICE_INPUT_EVENT:
            return {
                "inputs": [],
                "outputs": ["message_out"],
                "bidirectional": [],
            }
        elif self.type == NodeType.TEXT_OUTPUT:
            return {
                "inputs": ["message_in"],
                "outputs": [],
                "bidirectional": [],
            }
        elif self.type == NodeType.SCHEDULED_EVENT:
            return {
                "inputs": [],
                "outputs": ["message_out"],
                "bidirectional": [],
            }
        elif self.type == NodeType.MESSAGE_BUFFER:
            return {
                "inputs": ["message_in", "trigger"],
                "outputs": ["message_out"],
                "bidirectional": [],
            }
        return {"inputs": [], "outputs": [], "bidirectional": []}

