import argparse
import logging
from queue import Queue

from agent import Agent
from llm_adapter.llama_cpp_adapter import LlamaCppApiAdapter
from tools import ToolBox
from tools.math import Calculator
from tools.messaging.local import SendMessageToUser
from tools.system import Yield, GetDateAndTime, SelfReflect, SelfCritique
from tools.web import ScrapeWebsite, SearchWeb
from tools.tasks import MakePlan
from tools.memory import Recall


def configure_logging(debug):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    configure_logging(args.debug)

    event_queue = Queue()
    toolbox = ToolBox(
        [
            SendMessageToUser,
            Yield,
            SelfReflect,
            SelfCritique,
            Calculator,
            GetDateAndTime,
            # ScrapeWebsite,
            # SearchWeb,
            MakePlan,
            Recall,
        ]
    )
    adapter = LlamaCppApiAdapter()
    agent = Agent(adapter, toolbox, event_queue)
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
