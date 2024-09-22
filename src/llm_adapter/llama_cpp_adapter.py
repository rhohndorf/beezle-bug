import json
import requests

from llm_adapter import BaseAdapter
from memory import Observation
from tools.toolbox import ToolBox

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
        data = {"prompt": prompt, "grammar": grammar, "stop": ["<|im_end|>", "<|endoftext|>"]}
        response = requests.post(endpoint_url, headers=headers, json=data)
        data = response.json()
        return data["content"]

    def chat_completion(self, messages: list[Observation], tools: ToolBox) -> str:
        endpoint_url = f"{self.url}:{self.port}/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "messages": [message.model_dump() for message in messages],
            "grammar": tools.grammar,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        }
        response = requests.post(endpoint_url, headers=headers, json=data)
        data = response.json()
        return json.loads(data["choices"][0]["message"]["content"])
