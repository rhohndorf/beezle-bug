from datetime import datetime
from typing import List
from fastembed import TextEmbedding
from memory.memories import Observation


class MemoryStream:
    IMPORTANCE_THRESHOLD = 10

    def __init__(self) -> None:
        self.memories = []
        self.last_reflection_point = 0
        self.embedding_model = TextEmbedding()

    def add(self, role: str, statement: str) -> None:
        embedding = list(self.embedding_model.query_embed(statement))[0]
        observation = Observation(role, statement, 0.0, embedding)
        self.memories.append(observation)

    def retrieve(self, text: str, k: int) -> List[Observation]:
        current_time = datetime.now()
        text_embedding = list(self.embedding_model.query_embed(text))[0]
        retrieved_memories = sorted(self.memories, key=lambda x: x.score(text_embedding), reverse=True)[0:k]
        for mem in retrieved_memories:
            mem.accessed = current_time
        retrieved_memories.sort(key=lambda x: x.created)
        return retrieved_memories
