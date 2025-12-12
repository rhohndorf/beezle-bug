"""
Abstract base class for storage backends.

Defines the interface for async storage operations with support for:
- Project CRUD
- Knowledge Graph incremental operations
- Memory Stream incremental operations with vector search
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from beezle_bug.project import Project
    from beezle_bug.memory.knowledge_graph import KnowledgeGraph
    from beezle_bug.memory.memories import Observation


class StorageBackend(ABC):
    """
    Abstract async storage backend.
    
    All methods are async to support both SQLite (via aiosqlite) 
    and PostgreSQL (via asyncpg) backends.
    """
    
    # === Lifecycle ===
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database connection and create schema if needed."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close database connections."""
        ...
    
    # === Project Operations ===
    
    @abstractmethod
    async def list_projects(self) -> list[dict]:
        """
        List all projects with metadata.
        
        Returns:
            List of dicts with id, name, created_at, updated_at
        """
        ...
    
    @abstractmethod
    async def get_project(self, project_id: str) -> Optional["Project"]:
        """
        Get a project by ID.
        
        Returns:
            Project instance or None if not found
        """
        ...
    
    @abstractmethod
    async def save_project(self, project: "Project") -> None:
        """
        Save or update a project.
        
        The full project (including agent_graph, settings) is stored.
        """
        ...
    
    @abstractmethod
    async def delete_project(self, project_id: str) -> None:
        """
        Delete a project and all associated data.
        
        Cascades to delete knowledge_graphs, memory_streams, etc.
        """
        ...
    
    @abstractmethod
    async def project_exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        ...
    
    # === Knowledge Graph Operations ===
    
    @abstractmethod
    async def kg_ensure(self, project_id: str, node_id: str) -> int:
        """
        Ensure a knowledge graph exists for the given project/node.
        Creates if not exists.
        
        Returns:
            The knowledge_graph.id (integer primary key)
        """
        ...
    
    @abstractmethod
    async def kg_add_entity(
        self,
        kg_id: int,
        entity_name: str,
        properties: dict
    ) -> int:
        """
        Add an entity to the knowledge graph.
        
        Args:
            kg_id: Knowledge graph ID
            entity_name: Unique name for the entity
            properties: Entity properties as dict
            
        Returns:
            The entity.id (integer primary key)
        """
        ...
    
    @abstractmethod
    async def kg_update_entity(
        self,
        entity_id: int,
        properties: dict
    ) -> None:
        """
        Update entity properties.
        
        Args:
            entity_id: Entity ID
            properties: New properties (replaces existing)
        """
        ...
    
    @abstractmethod
    async def kg_add_entity_property(
        self,
        kg_id: int,
        entity_name: str,
        prop_name: str,
        prop_value: str
    ) -> None:
        """
        Add or update a single property on an entity.
        
        Args:
            kg_id: Knowledge graph ID
            entity_name: Entity name
            prop_name: Property name
            prop_value: Property value
        """
        ...
    
    @abstractmethod
    async def kg_remove_entity_property(
        self,
        kg_id: int,
        entity_name: str,
        prop_name: str
    ) -> None:
        """
        Remove a property from an entity.
        """
        ...
    
    @abstractmethod
    async def kg_remove_entity(self, kg_id: int, entity_name: str) -> None:
        """
        Remove an entity and all its relationships.
        
        Args:
            kg_id: Knowledge graph ID
            entity_name: Entity name to remove
        """
        ...
    
    @abstractmethod
    async def kg_get_entity_id(self, kg_id: int, entity_name: str) -> Optional[int]:
        """
        Get the entity ID by name.
        
        Returns:
            Entity ID or None if not found
        """
        ...
    
    @abstractmethod
    async def kg_add_relationship(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str,
        properties: dict
    ) -> int:
        """
        Add a relationship between two entities.
        
        Args:
            kg_id: Knowledge graph ID
            from_entity_name: Source entity name
            rel_type: Relationship type
            to_entity_name: Target entity name
            properties: Relationship properties
            
        Returns:
            The relationship.id (integer primary key)
        """
        ...
    
    @abstractmethod
    async def kg_update_relationship_property(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str,
        prop_name: str,
        prop_value: str
    ) -> None:
        """
        Add or update a property on a relationship.
        """
        ...
    
    @abstractmethod
    async def kg_remove_relationship_property(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str,
        prop_name: str
    ) -> None:
        """
        Remove a property from a relationship.
        """
        ...
    
    @abstractmethod
    async def kg_remove_relationship(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str
    ) -> None:
        """
        Remove a relationship between two entities.
        """
        ...
    
    @abstractmethod
    async def kg_load_full(
        self,
        project_id: str,
        node_id: str
    ) -> Optional["KnowledgeGraph"]:
        """
        Load the full knowledge graph into a KnowledgeGraph instance.
        
        Used for graph traversal operations that need the full graph in memory.
        
        Returns:
            KnowledgeGraph instance or None if not found
        """
        ...
    
    # === Memory Stream Operations ===
    
    @abstractmethod
    async def ms_ensure(self, project_id: str, node_id: str) -> int:
        """
        Ensure a memory stream exists for the given project/node.
        Creates if not exists.
        
        Returns:
            The memory_stream.id (integer primary key)
        """
        ...
    
    @abstractmethod
    async def ms_add_observation(
        self,
        ms_id: int,
        observation: "Observation"
    ) -> int:
        """
        Add an observation to the memory stream.
        
        Stores the observation data and its embedding vector.
        
        Args:
            ms_id: Memory stream ID
            observation: Observation instance with content and embedding
            
        Returns:
            The observation.id (integer primary key)
        """
        ...
    
    @abstractmethod
    async def ms_search(
        self,
        ms_id: int,
        query_embedding: list[float],
        k: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list["Observation"]:
        """
        Search for similar observations using vector similarity.
        
        Args:
            ms_id: Memory stream ID
            query_embedding: Query vector for similarity search
            k: Number of results to return
            from_date: Optional filter for created_at >= from_date
            to_date: Optional filter for created_at <= to_date
            
        Returns:
            List of Observation instances, sorted by similarity
        """
        ...
    
    @abstractmethod
    async def ms_update_accessed(
        self,
        observation_ids: list[int]
    ) -> None:
        """
        Update accessed_at timestamp for retrieved observations.
        
        Called after retrieval to update recency scores.
        """
        ...
    
    @abstractmethod
    async def ms_get_metadata(
        self,
        ms_id: int
    ) -> dict:
        """
        Get memory stream metadata.
        
        Returns:
            Dict with last_reflection_point, etc.
        """
        ...
    
    @abstractmethod
    async def ms_update_metadata(
        self,
        ms_id: int,
        metadata: dict
    ) -> None:
        """
        Update memory stream metadata.
        """
        ...






