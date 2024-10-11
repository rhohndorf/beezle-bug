import json


class WorkingMemory:
    def __init__(self) -> None:
        self.store = {}

    def add(self, key: str, value: str) -> str:
        if key not in self.store:
            self.store[key] = value
            return f"{key}:{value} added succesfully"
        return f"Error: key {key} already exists"

    def update(self, key: str, value: str) -> str:
        if key in self.store:
            self.store[key] = value
            return f"{key}:{value} updated succesfully"
        return f"Error: key {key} does not exist"

    def delete(self, key: str) -> str:
        if key in self.store:
            del self.store[key]
            return f"{key} deleted succesfully"
        return f"Error: key {key} does not exist"

    def __str__(self) -> str:
        return json.dumps(self.store)
