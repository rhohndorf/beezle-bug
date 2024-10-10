import requests

from beezle_bug.llm_adapter import BaseAdapter

DEFAULT_URL = "http://localhost"
DEFAULT_PORT = 8080


class LlamaCppApiAdapter(BaseAdapter):
    def __init__(self, url: str = DEFAULT_URL, port: int = DEFAULT_PORT) -> None:
        self.url = url
        self.port = port
        super().__init__()

    def completion(self, prompt, grammar) -> str:
        endpoint_url = f"{self.url}:{self.port}/completion"
        headers = {"Content-Type": "application/json"}
        data = {"prompt": prompt, "grammar": grammar, "stop": ["<|im_end|>"]}
        response = requests.post(endpoint_url, headers=headers, json=data)
        data = response.json()
        return data["content"]

    def chat_completion(self):
        pass
