import requests
import logging

from beezle_bug.llm_adapter import BaseAdapter

DEFAULT_URL = "http://localhost"
DEFAULT_PORT = 8080


class LlamaCppApiAdapter(BaseAdapter):
    def __init__(self, llm_config, url: str = DEFAULT_URL, port: int = DEFAULT_PORT) -> None:
        self.llm_config = llm_config
        self.url = url
        self.port = port
        super().__init__()

    def completion(self, messages, grammar) -> str:
        endpoint_url = f"{self.url}:{self.port}/completion"
        headers = {"Content-Type": "application/json"}
        prompt = self.llm_config.template.render(llm=self.llm_config, messages=messages)
        logging.debug(prompt)
        data = {"prompt": prompt, "grammar": grammar, "stop": self.llm_config.msg_stop}
        response = requests.post(endpoint_url, headers=headers, json=data)
        data = response.json()
        return data["content"]

    def chat_completion(self):
        pass
