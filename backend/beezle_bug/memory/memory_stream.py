"""
Memory stream module for storing conversational observations.

When a storage backend is provided, observations are persisted immediately
and retrieval uses vector similarity search in the database.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from fastembed import TextEmbedding

from beezle_bug.memory.memories import Observation
from beezle_bug.llm_adapter import Message, ToolCallResult, Response

if TYPE_CHECKING:
    from beezle_bug.storage.base import StorageBackend


class MemoryStream:
    """
    A memory stream for storing and retrieving conversational observations.
    
    Observations are stored with embeddings for semantic similarity search.
    When initialized with a storage backend, observations are persisted
    immediately to the database and retrieval uses vector search.
    
    Attributes:
        IMPORTANCE_THRESHOLD: Threshold for importance scoring
    """
    
    IMPORTANCE_THRESHOLD = 10

    def __init__(
        self,
        storage: Optional["StorageBackend"] = None,
        ms_id: Optional[int] = None
    ) -> None:
        """
        Initialize a memory stream.
        
        Args:
            storage: Optional storage backend for persistence
            ms_id: Database ID of this memory stream (required if storage is provided)
        """
        self._storage = storage
        self._ms_id = ms_id
        self.memories: List[Observation] = []  # In-memory cache (used as fallback)
        self.last_reflection_point = 0
        # Use persistent cache directory for embedding model
        self.embedding_model = TextEmbedding(cache_dir="/cache/fastembed")

    async def add(self, content: Message | ToolCallResult | Response) -> None:
        """
        Add a new observation to the memory stream.
        
        Creates an embedding for the content and persists immediately
        if a storage backend is configured.
        
        Args:
            content: The message, tool call result, or response to store
        """
        # Generate embedding
        content_json = content.model_dump_json() if hasattr(content, 'model_dump_json') else content.json()
        embedding = list(self.embedding_model.query_embed(content_json))[0]
        
        observation = Observation(content=content, embedding=embedding)
        
        # Persist to database
        if self._storage and self._ms_id:
            await self._storage.ms_add_observation(self._ms_id, observation)
        else:
            # Fallback to in-memory storage
            self.memories.append(observation)

    async def retrieve(
        self,
        text: str,
        k: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Observation]:
        """
        Retrieve the most relevant observations for the given text.
        
        Uses vector similarity search when storage backend is configured,
        otherwise falls back to in-memory search.
        
        Args:
            text: Query text to find similar observations
            k: Number of observations to retrieve
            from_date: Optional filter for created_at >= from_date
            to_date: Optional filter for created_at <= to_date
            
        Returns:
            List of observations sorted by creation time
        """
        # Generate query embedding
        query_embedding = list(self.embedding_model.query_embed(text))[0]
        
        if self._storage and self._ms_id:
            # Use database vector search
            observations = await self._storage.ms_search(
                self._ms_id,
                list(query_embedding),
                k,
                from_date,
                to_date
            )
            
            # Update accessed timestamps
            obs_ids = [getattr(obs, '_db_id', None) for obs in observations]
            obs_ids = [oid for oid in obs_ids if oid is not None]
            if obs_ids:
                await self._storage.ms_update_accessed(obs_ids)
            
            # Sort by creation time
            observations.sort(key=lambda x: x.created)
            return observations
        else:
            # Fallback to in-memory search
            return self._in_memory_retrieve(query_embedding, k, from_date, to_date)
    
    def _in_memory_retrieve(
        self,
        query_embedding: list,
        k: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Observation]:
        """
        In-memory retrieval using the original scoring algorithm.
        
        Used as fallback when no storage backend is configured.
        """
        current_time = datetime.now()
        
        # Filter by date range if specified
        filtered_memories = self.memories
        if from_date:
            filtered_memories = [m for m in filtered_memories if m.created >= from_date]
        if to_date:
            filtered_memories = [m for m in filtered_memories if m.created <= to_date]
        
        # Sort by combined score (recency + importance + relevance)
        retrieved_memories = sorted(
            filtered_memories,
            key=lambda x: x.score(query_embedding),
            reverse=True
        )[:k]
        
        # Update accessed timestamps
        for mem in retrieved_memories:
            mem.accessed = current_time
        
        # Sort by creation time for chronological output
        retrieved_memories.sort(key=lambda x: x.created)
        return retrieved_memories

    async def get_metadata(self) -> Dict[str, Any]:
        """
        Get memory stream metadata.
        
        Returns:
            Dict with last_reflection_point and other metadata
        """
        if self._storage and self._ms_id:
            return await self._storage.ms_get_metadata(self._ms_id)
        else:
            return {"last_reflection_point": self.last_reflection_point}
    
    async def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update memory stream metadata.
        
        Args:
            metadata: Dict with metadata to update
        """
        if "last_reflection_point" in metadata:
            self.last_reflection_point = metadata["last_reflection_point"]
        
        if self._storage and self._ms_id:
            await self._storage.ms_update_metadata(self._ms_id, metadata)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the memory stream to a dictionary.
        
        Note: This only serializes in-memory observations.
        For database-backed streams, use the storage backend directly.
        
        Returns:
            Dictionary representation of the memory stream
        """
        return {
            "last_reflection_point": self.last_reflection_point,
            "memories": [mem.to_dict() for mem in self.memories]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryStream':
        """
        Create a memory stream from a dictionary.
        
        Args:
            data: Dictionary representation of the memory stream
            
        Returns:
            New MemoryStream instance (in-memory only)
        """
        stream = cls()
        stream.last_reflection_point = data.get("last_reflection_point", 0)
        
        for mem_data in data.get("memories", []):
            observation = Observation.from_dict(mem_data)
            stream.memories.append(observation)
        
        return stream
