"""
SQLModel Node database model.
"""

from typing import TYPE_CHECKING, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON

if TYPE_CHECKING:
    from .project import ProjectDB


class NodeDB(SQLModel, table=True):
    """
    Database model for agent graph nodes.
    
    Maps to the 'nodes' table.
    """
    __tablename__ = "nodes"
    
    id: str = Field(primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    
    # Node type (agent, knowledge_graph, memory_stream, etc.)
    type: str = Field(index=True)
    
    # Position (split into columns for potential spatial queries)
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0)
    
    # Config is polymorphic based on node type, stored as JSON
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Relationship back to project
    project: Optional["ProjectDB"] = Relationship(back_populates="nodes")
    
    def to_pydantic(self) -> "Node":
        """Convert database model to Pydantic API model."""
        from beezle_bug.agent_graph.node import Node
        from beezle_bug.agent_graph.types import NodeType, Position
        
        # Import all config types for proper instantiation
        from beezle_bug.agent_graph.types import (
            AgentNodeConfig,
            KnowledgeGraphNodeConfig,
            MemoryStreamNodeConfig,
            ToolboxNodeConfig,
            TextInputNodeConfig,
            VoiceInputNodeConfig,
            TextOutputNodeConfig,
            ScheduledEventNodeConfig,
            WaitAndCombineNodeConfig,
        )
        
        # Map type string to config class
        config_classes = {
            "agent": AgentNodeConfig,
            "knowledge_graph": KnowledgeGraphNodeConfig,
            "memory_stream": MemoryStreamNodeConfig,
            "toolbox": ToolboxNodeConfig,
            "text_input": TextInputNodeConfig,
            "voice_input": VoiceInputNodeConfig,
            "text_output": TextOutputNodeConfig,
            "scheduled_event": ScheduledEventNodeConfig,
            "wait_and_combine": WaitAndCombineNodeConfig,
        }
        
        config_class = config_classes.get(self.type)
        if config_class:
            config = config_class(**self.config)
        else:
            # Fallback - shouldn't happen
            config = self.config
        
        return Node(
            id=self.id,
            type=NodeType(self.type),
            position=Position(x=self.position_x, y=self.position_y),
            config=config,
        )
    
    @classmethod
    def from_pydantic(cls, node: "Node", project_id: str) -> "NodeDB":
        """Create database model from Pydantic API model."""
        return cls(
            id=node.id,
            project_id=project_id,
            type=node.type.value,
            position_x=node.position.x,
            position_y=node.position.y,
            config=node.config.model_dump() if hasattr(node.config, 'model_dump') else dict(node.config),
        )

