from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import numpy as np
import math


# class BaseMemory(BaseModel):
#     DECAY: float = 0.999
#     created: datetime = Field(default_factory=datetime.now)
#     accessed: datetime = Field(default_factory=datetime.now)
#     importance: float
#     embedding: np.ndarray

#     @property
#     def recency(self) -> float:
#         elapsed_hours = (datetime.now() - self.accessed).total_seconds() / 3600
#         return 1.0 * math.exp(-self.DECAY * elapsed_hours)

#     def relevance(self, embedding: List[float]) -> float:
#         A = self.embedding
#         B = np.array(embedding)

#         dot_product = np.dot(A, B)
#         magnitude_A = np.linalg.norm(A)
#         magnitude_B = np.linalg.norm(B)

#         return dot_product / (magnitude_A * magnitude_B)

#     def score(self, embedding: List[float]) -> float:
#         return (self.recency + self.importance + self.relevance(embedding)) / 3.0


class Observation(BaseModel):
    role: str
    content: str

    def __str__(self):
        return f"{self.role}: {self.content}"

    def __repr__(self) -> str:
        return str(self)
