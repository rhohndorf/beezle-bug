import argparse
import logging
from queue import Queue

from beezle_bug.agent import Agent
from beezle_bug.llm_adapter.llama_cpp_adapter import LlamaCppApiAdapter
from beezle_bug.tools import ToolBox
from beezle_bug.tools.math import Calculator
from beezle_bug.tools.messaging import SendMessage
from beezle_bug.tools.system import Yield, GetDateAndTime, SelfReflect, SelfCritique
from beezle_bug.tools.web import ScrapeWebsite, SearchWeb
from beezle_bug.tools.tasks import MakePlan
from beezle_bug.tools.memory import Recall, AddWorkingMemory, UpdateWorkingMemory, DeleteWorkingMemory


def configure_logging(debug):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)

def user_input():
    while True:
        user_message = input("> ")
        message_queue.put(("user", user_message))
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    configure_logging(args.debug)

    messages = Queue()
    toolbox = ToolBox(
        [
            SendMessage,
            # Yield,
            # SelfReflect,
            # SelfCritique,
            # Calculator,
            # GetDateAndTime,
            # ScrapeWebsite,
            # SearchWeb,
            # MakePlan,
            # # Recall,
            # AddWorkingMemory,
            # UpdateWorkingMemory,
            # DeleteWorkingMemory,
        ]
    )
    adapter = LlamaCppApiAdapter()
    agent = Agent(adapter, toolbox)
    agent.add_contact("User", messages)
    agent.start()

    while True:
        user_input = input("USER> ")

        if user_input == "/exit":
            break
        elif user_input == "/stop":
            agent.stop()
        elif user_input == "/start":
            agent.start()
        else:
            event_queue.put(user_input)

    agent.stop()


if __name__ == "__main__":
    main()
