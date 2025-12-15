"""
Memory stream module for storing conversational observations.

Observations are persisted to the database immediately and retrieval
uses vector similarity search.
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
    All observations are persisted to the database immediately.
    
    Attributes:
        IMPORTANCE_THRESHOLD: Threshold for importance scoring
    """
    
    IMPORTANCE_THRESHOLD = 10

    def __init__(
        self,
        storage: "StorageBackend",
        ms_id: int
    ) -> None:
        """
        Initialize a memory stream.
        
        Args:
            storage: Storage backend for persistence (required)
            ms_id: Database ID of this memory stream (required)
        """
        self._storage = storage
        self._ms_id = ms_id
        self.last_reflection_point = 0
        # Use persistent cache directory for embedding model
        self.embedding_model = TextEmbedding(cache_dir="/cache/fastembed")

    async def add(self, content: Message | ToolCallResult | Response) -> None:
        """
        Add a new observation to the memory stream.
        
        Creates an embedding for the content and persists to the database.
        
        Args:
            content: The message, tool call result, or response to store
        """
        # Generate embedding
        content_json = content.model_dump_json() if hasattr(content, 'model_dump_json') else content.json()
        embedding = list(self.embedding_model.query_embed(content_json))[0]
        
        observation = Observation(content=content, embedding=embedding)
        
        # Persist to database
        await self._storage.ms_add_observation(self._ms_id, observation)

    async def retrieve(
        self,
        text: str,
        k: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Observation]:
        """
        Retrieve the most relevant observations for the given text.
        
        Uses vector similarity search in the database.
        
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

    async def retrieve_recent(self, n: int) -> List[Observation]:
        """
        Retrieve the N most recent observations.
        
        Returns observations in chronological order (oldest first).
        
        Args:
            n: Number of observations to retrieve
            
        Returns:
            List of observations sorted by creation time (oldest first)
        """
        return await self._storage.ms_get_recent(self._ms_id, n)

    async def get_metadata(self) -> Dict[str, Any]:
        """
        Get memory stream metadata.
        
        Returns:
            Dict with last_reflection_point and other metadata
        """
        return await self._storage.ms_get_metadata(self._ms_id)
    
    async def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update memory stream metadata.
        
        Args:
            metadata: Dict with metadata to update
        """
        if "last_reflection_point" in metadata:
            self.last_reflection_point = metadata["last_reflection_point"]
        
        await self._storage.ms_update_metadata(self._ms_id, metadata)
