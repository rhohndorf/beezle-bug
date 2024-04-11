import logging
import json
from queue import Queue
from threading import Thread
import time

from llm_adapter import BaseAdapter
from memory import MemoryStream
from memory import WorkingMemory
import prompt_template
from tools import ToolBox

DEFAULT_SYSTEM_MESSAGE = """
You are Beezle Bug the AI assistant. You have a rough and sloppy personality.

During each execution cycle do one of the following:

1. If you don't have a current task, identify a task to do
2. If you dont have a plan yet how to solve the task create one.
3. Execute the plan and the next plan step
4. Assess the result of the last executed step
5. Go to the next plan step
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
            if not self.event_queue.empty():
                user_input = self.event_queue.get()
                self.memory_stream.add("user", user_input)

            system_message = DEFAULT_SYSTEM_MESSAGE.format(docs=self.toolbox.docs, wmem=self.working_memory)
            prompt = self.prompt_template.render(system=system_message, messages=self.memory_stream.memories[-10:])
            logging.debug(prompt)

            selected_tool = json.loads(self.adapter.completion(prompt, self.toolbox.grammar))
            logging.debug(selected_tool)
            tool = self.toolbox.get_tool(selected_tool)
            result = tool.run(self)

            if result is not None:
                self.memory_stream.add("assistant", f"{selected_tool['function']}: {result}")

            time.sleep(DEFAULT_PERIOD)
