from datetime import datetime
from typing import List

# from memory.memories import Observation


class MemoryStream:
    IMPORTANCE_THRESHOLD = 10

    def __init__(self) -> None:
        self.memories = []
        self.last_reflection_point = 0

    # def _assignImportanceValue(self, statement: str) -> float:
    #     context = self.memories[-1].content if len(self.memories) > 0 else ""
    #     importance = llm.generate(
    #         prompt_template="importance",
    #         prompt_data={"context": context, "statement": statement},
    #         grammar="one-to-ten",
    #     )
    #     return float(importance) / 10.0

    # def _needs_reflection(self) -> bool:
    #     return (
    #         sum(mem.importance for mem in self.memories[self.last_reflection_point :])
    #         > MemoryStream.IMPORTANCE_THRESHOLD
    #     )

    # def _reflect(self) -> None:
    #     prompt_data = {"memories": "".join([mem.content for mem in self.memories[self.last_reflection_point :]])}
    #     questions = llm.generate(prompt_template="reflection_candidate_questions", prompt_data=prompt_data)
    #     print(questions)
    #     self.last_reflection_point = len(self.memories) - 1

    def add(self, statement: str) -> None:
        self.memories.append(statement)

    def __str__(self) -> str:
        memory_strings = ""
        for mem in self.memories[-100:]:
            memory_strings += mem + "\n"
        return memory_strings

    #     importance = self._assignImportanceValue(statement)
    #     embedding = llm.embed(statement)
    #     observation = Observation(statement, importance, embedding)
    #     self.memories.append(observation)
    #     if self._needs_reflection():
    #         self._reflect()

    # def retrieve(self, text: str, k: int) -> List[Observation]:
    #     current_time = datetime.now()
    #     text_embedding = llm.embed(text)
    #     retrieved_memories = sorted(self.memories, key=lambda x: x.score(text_embedding), reverse=True)[0:k]
    #     for mem in retrieved_memories:
    #         mem.accessed = current_time
    #     retrieved_memories.sort(key=lambda x: x.created)
    #     return retrieved_memories
