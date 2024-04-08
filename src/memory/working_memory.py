import json


class WorkingMemory:
    def __init__(self) -> None:
        self.store = {}

    def add(self, key: str, value: str):
        self.store[key] = value

    def update(self, key: str, value: str):
        self.store[key] = value

    def delete(self, key: str):
        del self.store[key]

    def __str__(self) -> str:
        return json.dumps(self.store)
