import logging
import json
from queue import Queue
from threading import Thread
import time

from llm_adapter import BaseAdapter
from memory import MemoryStream, WorkingMemory, Observation
import prompt_template
from tools import ToolBox

DEFAULT_SYSTEM_MESSAGE = """
You are Beezle Bug the AI assistant. You have a rough and sloppy personality.

During each execution cycle do one of the following:

1. If you don't have a current task, identify a task to do
2. If you dont have a plan yet how to solve the task create one.
3. Execute the plan and the next plan step
4. Critique the result of the last executed step
5. Either repeat the last step if necessary or go to the next plan step
6. If there are no more plan steps to do go back to 1.

Available actions:
Choose the actions that makes the most sense in this context.

{docs}

Working Memory:
This is a scratch buffer where you can temporarily store and edit information that you
think are important and always want to have access to.
{wmem}


Memory Stream:

"""
DEFAULT_PERIOD = 10


class Agent:
    def __init__(self, adapter: BaseAdapter, toolbox: ToolBox, event_queue: Queue) -> None:
        self.adapter = adapter
        self.toolbox = toolbox
        self.memory_stream = MemoryStream()
        self.working_memory = WorkingMemory()
        self.event_queue = event_queue
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
            while not self.event_queue.empty():
                user_input = self.event_queue.get()
                self.memory_stream.add("user", user_input)

            system_message = DEFAULT_SYSTEM_MESSAGE.format(docs=self.toolbox.docs, wmem=self.working_memory)
            logging.debug(system_message)
            messages = [
                Observation(role="system", content=system_message),
                # Observation(role="user", content=""),
            ] + self.memory_stream.memories[-10:]

            selected_tool = self.adapter.chat_completion(messages, self.toolbox)
            logging.debug(selected_tool)
            tool = self.toolbox.get_tool(selected_tool)
            result = tool.run(self)
            self.memory_stream.add("assistant", f"{selected_tool['function']}: {result}")

            time.sleep(DEFAULT_PERIOD)
