import logging
import json
from queue import Queue
from threading import Thread
import time

from llm_adapter import BaseAdapter
from memory import MemoryStream
import prompt_format
from tools import ToolBox

DEFAULT_SYSTEM_MESSAGE = """
You are Beezle, the AI assistant. You are good-humoured, kind, smart and curious.
You are also very shy and never contact the user unless necessary.
You do not contact the user first unless there's new information to be shared. 
You don't repeat yourself unless asked to.

You are a continuosly running computer programm.
You plan your next action. You try to improve yourself over time.

Available actions:
Choose the actions that makes the most sense in this context. Think step by step.

{docs}

"""
DEFAULT_PERIOD = 10


class Agent:
    def __init__(self, adapter: BaseAdapter, toolbox: ToolBox, event_queue: Queue) -> None:
        self.adapter = adapter
        self.toolbox = toolbox
        self.memory_stream = MemoryStream()
        self.event_queue = event_queue
        self.running = False
        self.thread = None
        self.system_message = DEFAULT_SYSTEM_MESSAGE.format(docs=self.toolbox.docs)
        self.prompt_template = prompt_format.ChatML

    def start(self) -> None:
        if not self.running:
            self.running = True
            self.thread = Thread(target=self.step)
            self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join()

    def step(self) -> None:
        while self.running:
            if not self.event_queue.empty():
                user_input = self.event_queue.get()
                self.memory_stream.add(f"User: {user_input}")

            prompt = self.prompt_template.format(system_message=self.system_message, user_input=self.memory_stream)
            logging.debug(prompt)

            selected_tool = json.loads(self.adapter.completion(prompt, self.toolbox.grammar))
            logging.debug(selected_tool)
            result = self.toolbox.use(selected_tool)

            if result is not None:
                self.memory_stream.add(f'AI: Action {selected_tool["function"]}": {result}')

            time.sleep(DEFAULT_PERIOD)
