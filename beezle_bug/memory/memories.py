from datetime import datetime
from typing import List

import math
import numpy as np


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


class Observation(BaseMemory):
    def __init__(self, role: str, fact: str, importance: float, embedding: np.ndarray) -> None:
        super().__init__(importance, embedding)
        self.content = fact
        self.role = role

    def __str__(self):
        return f"{self.role}: {self.content}"

    def __repr__(self) -> str:
        return str(self)
