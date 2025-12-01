from datetime import datetime
from typing import List, Dict, Any
import math
import numpy as np
from pydantic import BaseModel, Field
from collections.abc import Iterable

from beezle_bug.llm_adapter import Message, ToolCallResult, Response

class BaseMemory:
    DECAY = 0.999

    def __init__(self, importance: float, embedding: np.ndarray) -> None:
        self.created = datetime.now()
        self.accessed = datetime.now()
        self.importance = importance
        self.embedding = embedding

    @property
    def recency(self) -> float:
        elapsed_hours = (datetime.now() - self.accessed).total_seconds() / 3600
        return 1.0 * math.exp(-BaseMemory.DECAY * elapsed_hours)

    def relevance(self, embedding: List[float]) -> float:
        # Define your vectors A and B as NumPy arrays
        A = self.embedding
        B = embedding

        # Calculate the dot product
        dot_product = np.dot(A, B)

        # Calculate the magnitudes of the vectors
        magnitude_A = np.linalg.norm(A)
        magnitude_B = np.linalg.norm(B)

        # Calculate the cosine similarity
        return dot_product / (magnitude_A * magnitude_B)

    def score(self, embedding: List[float]):
        return (self.recency + self.importance + self.relevance(embedding)) / 3.0


class Observation(BaseModel):
    created: datetime = Field(default_factory=datetime.now)
    accessed: datetime = Field(default_factory=datetime.now)
    importance: float = Field(default=0.0)
    embedding: Iterable
    content: Message|ToolCallResult|Response

    @property
    def recency(self) -> float:
        elapsed_hours = (datetime.now() - self.accessed).total_seconds() / 3600
        return 1.0 * math.exp(-BaseMemory.DECAY * elapsed_hours)

    def relevance(self, embedding: List[float]) -> float:
        # Define your vectors A and B as NumPy arrays
        A = self.embedding
        B = embedding

        # Calculate the dot product
        dot_product = np.dot(A, B)

        # Calculate the magnitudes of the vectors
        magnitude_A = np.linalg.norm(A)
        magnitude_B = np.linalg.norm(B)

        # Calculate the cosine similarity
        return dot_product / (magnitude_A * magnitude_B)

    def score(self, embedding: List[float]):
        return (self.recency + self.importance + self.relevance(embedding)) / 3.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the observation to a dictionary."""
        content_data = self.content.model_dump() if hasattr(self.content, 'model_dump') else self.content.dict()
        content_type = type(self.content).__name__
        
        # Convert numpy array to list of Python floats for JSON serialization
        if hasattr(self.embedding, 'tolist'):
            # numpy array - use tolist() which converts to native Python types
            embedding_list = self.embedding.tolist()
        elif hasattr(self.embedding, '__iter__'):
            # Other iterable - convert each element to float
            embedding_list = [float(x) for x in self.embedding]
        else:
            embedding_list = self.embedding
        
        return {
            "created": self.created.isoformat(),
            "accessed": self.accessed.isoformat(),
            "importance": float(self.importance),  # Ensure importance is also a Python float
            "embedding": embedding_list,
            "content_type": content_type,
            "content": content_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Observation':
        """Create an observation from a dictionary."""
        content_type = data.get("content_type", "Message")
        content_data = data.get("content", {})
        
        # Reconstruct the content object
        if content_type == "Message":
            content = Message(**content_data)
        elif content_type == "ToolCallResult":
            content = ToolCallResult(**content_data)
        elif content_type == "Response":
            content = Response(**content_data)
        else:
            # Fallback to Message
            content = Message(**content_data)
        
        return cls(
            created=datetime.fromisoformat(data["created"]) if isinstance(data.get("created"), str) else data.get("created", datetime.now()),
            accessed=datetime.fromisoformat(data["accessed"]) if isinstance(data.get("accessed"), str) else data.get("accessed", datetime.now()),
            importance=data.get("importance", 0.0),
            embedding=np.array(data.get("embedding", [])),
            content=content
        )
