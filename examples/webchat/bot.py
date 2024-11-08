import asyncio
from logging import debug, basicConfig, DEBUG, INFO
import socketio
from queue import Queue
import argparse

from beezle_bug.agent import Agent
from beezle_bug.llm_adapter.llama_cpp_adapter import LlamaCppApiAdapter
from beezle_bug.llm_config import LLAMA, GEMMA
from beezle_bug.tools import ToolBox
from beezle_bug.tools.messaging import SendMessage
from beezle_bug.tools.memory.memory_stream import Recall
from beezle_bug.tools.memory.knowledge_graph import (
    AddEntity,
    AddPropertyToEntity,
    AddRelationship,
    # UpdateEntityPropertiesInKnowledgeGraph,
    GetRelationships,
    GetEntity,
)
from beezle_bug.tools.os.filesystem import GetFileList, ReadTextFile, WriteTextFile
from beezle_bug.tools.python import ExecPythonCode
from beezle_bug.tools.system import Wait, GetDateAndTime, SelfReflect, SelfCritique, Reason, SetEngagement
from beezle_bug.tools.tasks import MakePlan
from beezle_bug.tools.web import ReadWebsite, SearchWeb
from beezle_bug.tools.wikipedia import SearchWikipedia, GetWikipediaPageSummary

# Async Socket.IO client
sio = socketio.AsyncClient()


# Handle connection event
@sio.event
async def connect():
    print("Connected to the server!")


# Handle disconnection event
@sio.event
async def disconnect():
    print("Disconnected from server!")


# Handle custom chat message event
@sio.event
async def chat_message(data):
    if data["user"] != agent.name:
        agent.send_message((data["user"], data["message"]))


# Send message to server
async def send_messages():
    while True:
        if not messages.empty():
            message = messages.get()
            await sio.emit("send_message", {"user": agent.name, "message": message})
        await asyncio.sleep(0.1)


# Main function to handle the client connection and tasks
async def start_client():
    await sio.connect("http://localhost:5000")
    await send_messages()


if __name__ == "__main__":
    # Use argparse to handle command-line parameters 'name' and 'debug'
    parser = argparse.ArgumentParser(description="Start Beezle Bug Agent with a custom name and debug mode.")
    parser.add_argument("--name", type=str, help="Name for the agent", default="")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Configure logging level based on debug mode
    if args.debug:
        basicConfig(level=DEBUG)
        debug("Debug mode is enabled.")
    else:
        basicConfig(level=INFO)

    messages = Queue()

    toolbox = ToolBox(
        [
            SendMessage,
            Reason,
            Wait,
            # SetEngagement,
            SelfReflect,
            SelfCritique,
            ExecPythonCode,
            # GetDateAndTime,
            SearchWikipedia,
            GetWikipediaPageSummary,
            ReadWebsite,
            SearchWeb,
            MakePlan,
            Recall,
            AddEntity,
            AddPropertyToEntity,
            AddRelationship,
            GetEntity,
            GetRelationships,
            # UpdateEntityPropertiesInKnowledgeGraph,
            # AddWorkingMemory,
            # UpdateWorkingMemory,
            # DeleteWorkingMemory,
            # GetFileList,
            # ReadTextFile,
            # WriteTextFile,
        ]
    )
    adapter = LlamaCppApiAdapter(GEMMA)
    agent = Agent(adapter, toolbox, name=args.name)
    agent.add_contact("Chatroom", messages)
    agent.start()

    asyncio.run(start_client())
