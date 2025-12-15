"""
SQLModel Project database model.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON

if TYPE_CHECKING:
    from .node import NodeDB
    from .edge import EdgeDB


class ProjectDB(SQLModel, table=True):
    """
    Database model for projects.
    
    Maps to the 'projects' table with proper columns instead of JSON blob.
    """
    __tablename__ = "projects"
    
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    
    # Settings stored as JSON (1:1 relationship, simple structure)
    tts_settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    stt_settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    nodes: List["NodeDB"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    edges: List["EdgeDB"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    def to_pydantic(self) -> "Project":
        """Convert database model to Pydantic API model."""
        from beezle_bug.project import Project, TTSSettings, STTSettings
        from beezle_bug.agent_graph import AgentGraph, Node, Edge
        from beezle_bug.agent_graph.types import Position
        
        # Convert nodes
        nodes = []
        for node_db in self.nodes:
            nodes.append(node_db.to_pydantic())
        
        # Convert edges
        edges = []
        for edge_db in self.edges:
            edges.append(edge_db.to_pydantic())
        
        return Project(
            id=self.id,
            name=self.name,
            agent_graph=AgentGraph(nodes=nodes, edges=edges),
            tts_settings=TTSSettings(**self.tts_settings) if self.tts_settings else TTSSettings(),
            stt_settings=STTSettings(**self.stt_settings) if self.stt_settings else STTSettings(),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
    
    @classmethod
    def from_pydantic(cls, project: "Project") -> "ProjectDB":
        """Create database model from Pydantic API model."""
        return cls(
            id=project.id,
            name=project.name,
            tts_settings=project.tts_settings.model_dump(),
            stt_settings=project.stt_settings.model_dump(),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

