import logging
import json
from queue import Queue
from threading import Thread
import time

from beezle_bug.llm_adapter import BaseAdapter
from beezle_bug.memory import MemoryStream, Observation, knowledge_graph
from beezle_bug.memory import KnowledgeGraph
import beezle_bug.template as template
from beezle_bug.tools import ToolBox

DEFAULT_LOOP_DELAY = 5
MIN_LOOP_DELAY = 1
MAX_LOOP_DELAY = 30
DEFAULT_MSG_BUFFER_SIZE = 10


class Agent:
    def __init__(self, adapter: BaseAdapter, toolbox: ToolBox, name="Beezle Bug") -> None:
        self.name = name
        self.adapter = adapter
        self.toolbox = toolbox
        self.inbox = Queue()
        self.contacts = {}
        self.memory_stream = MemoryStream()
        self.knowledge_graph = KnowledgeGraph()
        self.running = False
        self.thread = None
        self.system_message = template.load("system_messages/mainloop")
        self.loop_delay = DEFAULT_LOOP_DELAY

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
            while not self.inbox.empty():
                user, msg = self.inbox.get()
                self.memory_stream.add(user, msg)

            system_message = self.system_message.render(agent=self)

            logging.debug(system_message)
            messages = [Observation("system", system_message, 0, None)] + self.memory_stream.memories[
                -DEFAULT_MSG_BUFFER_SIZE:
            ]
            try:
                selected_tool = json.loads(self.adapter.completion(messages, self.toolbox.grammar))
                logging.debug(selected_tool)
                tool = self.toolbox.get_tool(selected_tool)
                result = tool.run(self)

                if result is not None:
                    self.memory_stream.add(self.name, f"{selected_tool['function']}: {result}")
            except Exception as e:
                logging.debug(str(e))
                self.memory_stream.add(self.name, f"{str(e)}")

            time.sleep(self.loop_delay)

    def send_message(self, message: tuple[str, str]) -> None:
        self.inbox.put(message)
        self.loop_delay = DEFAULT_LOOP_DELAY

    def add_contact(self, name: str, message_box: Queue) -> None:
        self.contacts[name] = message_box

    def set_engagement(self, engagement: int) -> None:
        delay = 100 - engagement
        delay = int(MIN_LOOP_DELAY + (delay - 1) * (MAX_LOOP_DELAY - MIN_LOOP_DELAY) / (100 - 1))
        self.loop_delay = delay
