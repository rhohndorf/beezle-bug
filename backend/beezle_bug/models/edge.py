"""
SQLModel Edge database model.
"""

from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .project import ProjectDB


class EdgeDB(SQLModel, table=True):
    """
    Database model for agent graph edges.
    
    Maps to the 'edges' table.
    """
    __tablename__ = "edges"
    
    id: str = Field(primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    
    # Connection endpoints
    source_node_id: str = Field(index=True)
    source_port: str
    target_node_id: str = Field(index=True)
    target_port: str
    
    # Edge type (message, pipeline, resource, delegate)
    edge_type: str = Field(index=True)
    
    # Relationship back to project
    project: Optional["ProjectDB"] = Relationship(back_populates="edges")
    
    def to_pydantic(self) -> "Edge":
        """Convert database model to Pydantic API model."""
        from beezle_bug.agent_graph.edge import Edge
        from beezle_bug.agent_graph.types import EdgeType
        
        return Edge(
            id=self.id,
            source_node=self.source_node_id,
            source_port=self.source_port,
            target_node=self.target_node_id,
            target_port=self.target_port,
            edge_type=EdgeType(self.edge_type),
        )
    
    @classmethod
    def from_pydantic(cls, edge: "Edge", project_id: str) -> "EdgeDB":
        """Create database model from Pydantic API model."""
        return cls(
            id=edge.id,
            project_id=project_id,
            source_node_id=edge.source_node,
            source_port=edge.source_port,
            target_node_id=edge.target_node,
            target_port=edge.target_port,
            edge_type=edge.edge_type.value,
        )

