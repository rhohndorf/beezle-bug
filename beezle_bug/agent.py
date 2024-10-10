import logging
import json
from queue import Queue
from threading import Thread
import time

from beezle_bug.llm_adapter import BaseAdapter
from beezle_bug.memory import MemoryStream
from beezle_bug.memory import WorkingMemory
import beezle_bug.prompt_template as prompt_template
from beezle_bug.tools import ToolBox

DEFAULT_SYSTEM_MESSAGE = """
You are {name} the expert AI assistant that explains its reasoning step by step. 
You solve problems be first reasonig about them and then reporting the final answer.
Decide if you need another step or if you're ready to give the final answer.
USE AS MANY REASONING STEPS AS POSSIBLE. AT LEAST 3. BE AWARE OF YOUR LIMITATIONS AS AN LLM AND WHAT YOU CAN AND CANNOT DO. 
IN YOUR REASONING, INCLUDE EXPLORATION OF ALTERNATIVE ANSWERS. CONSIDER YOU MAY BE WRONG, AND IF YOU ARE WRONG IN YOUR REASONING, WHERE IT WOULD BE. FULLY TEST ALL OTHER POSSIBILITIES. 
YOU CAN BE WRONG. WHEN YOU SAY YOU ARE RE-EXAMINING, ACTUALLY RE-EXAMINE, AND USE ANOTHER APPROACH TO DO SO. 
DO NOT JUST SAY YOU ARE RE-EXAMINING. USE AT LEAST 3 METHODS TO DERIVE THE ANSWER. USE BEST PRACTICES.


You can send messages to the following contacts:
{contacts}

Available actions:
Choose the actions that makes the most sense in this context.

{docs}

Working Memory:
This is a scratch buffer where you can temporarily store and edit information that you
think are important and always want to have access to.
{wmem}


Memory Stream:

"""
DEFAULT_PERIOD = 5


class Agent:
    def __init__(self, adapter: BaseAdapter, toolbox: ToolBox, name="Beezle Bug") -> None:
        self.name = name
        self.adapter = adapter
        self.toolbox = toolbox
        self.inbox = Queue()
        self.contacts = {}
        self.memory_stream = MemoryStream()
        self.working_memory = WorkingMemory()
        self.running = False
        self.thread = None
        self.prompt_template = prompt_template.load(prompt_template.CHATML)

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

            system_message = DEFAULT_SYSTEM_MESSAGE.format(
                name=self.name,
                docs=self.toolbox.docs,
                wmem=self.working_memory,
                contacts=list(self.contacts.keys()),
            )
            prompt = self.prompt_template.render(
                agent_name=self.name, system=system_message, messages=self.memory_stream.memories[-100:]
            )
            logging.debug(prompt)

            try:
                selected_tool = json.loads(self.adapter.completion(prompt, self.toolbox.grammar))
                logging.debug(selected_tool)
                tool = self.toolbox.get_tool(selected_tool)
                result = tool.run(self)

                if result is not None:
                    self.memory_stream.add(self.name, f"{selected_tool['function']}: {result}")
            except Exception as e:
                logging.exception(e)

            time.sleep(DEFAULT_PERIOD)

    def send_message(self, message: tuple[str, str]) -> None:
        self.inbox.put(message)

    def add_contact(self, name: str, message_box: Queue) -> None:
        self.contacts[name] = message_box
