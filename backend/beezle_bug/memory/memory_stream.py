from datetime import datetime
from typing import List, Dict, Any
from fastembed import TextEmbedding

from beezle_bug.memory.memories import Observation
from beezle_bug.llm_adapter import Message, ToolCallResult

class MemoryStream:
    IMPORTANCE_THRESHOLD = 10

    def __init__(self) -> None:
        self.memories: List[Observation] = []
        self.last_reflection_point = 0
        # Use persistent cache directory
        self.embedding_model = TextEmbedding(cache_dir="/cache/fastembed")

    def add(self, content: Message|ToolCallResult) -> None:
        embedding = list(self.embedding_model.query_embed(content.json()))[0]
        observation = Observation(content=content, embedding=embedding)
        self.memories.append(observation)

    def retrieve(self, text: str, k: int) -> List[Observation]:
        current_time = datetime.now()
        text_embedding = list(self.embedding_model.query_embed(text))[0]
        retrieved_memories = sorted(self.memories, key=lambda x: x.score(text_embedding), reverse=True)[0:k]
        for mem in retrieved_memories:
            mem.accessed = current_time
        retrieved_memories.sort(key=lambda x: x.created)
        return retrieved_memories

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the memory stream to a dictionary.
        
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
            New MemoryStream instance
        """
        stream = cls()
        stream.last_reflection_point = data.get("last_reflection_point", 0)
        
        for mem_data in data.get("memories", []):
            observation = Observation.from_dict(mem_data)
            stream.memories.append(observation)
        
        return stream
