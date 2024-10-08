import asyncio
from logging import debug
import socketio
from queue import Queue

from beezle_bug.agent import Agent
from beezle_bug.llm_adapter.llama_cpp_adapter import LlamaCppApiAdapter
from beezle_bug.tools import ToolBox
from beezle_bug.tools.math import Calculator
from beezle_bug.tools.messaging import SendMessage
from beezle_bug.tools.system import Yield, GetDateAndTime, SelfReflect, SelfCritique, Reason
from beezle_bug.tools.web import ScrapeWebsite, SearchWeb
from beezle_bug.tools.tasks import MakePlan
from beezle_bug.tools.memory import Recall, AddWorkingMemory, UpdateWorkingMemory, DeleteWorkingMemory

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
    agent.send_message(data['message'])
    print(f"Server: {data['user']}: {data['message']}")

# Send message to server
async def send_messages():
    while True:
        if not messages.empty():
            message = messages.get()
            await sio.emit('send_message', {'user': 'PythonClient', 'message': message})
        await asyncio.sleep(0.1) 



# Main function to handle the client connection and tasks
async def start_client():
    await sio.connect('http://localhost:5000')
    # Start sending messages
    await send_messages()

if __name__ == "__main__":
    debug = True
    messages = Queue()
    toolbox = ToolBox(
        [
            SendMessage,
            Reason,
            # Yield,
            # SelfReflect,
            # SelfCritique,
            # Calculator,
            # GetDateAndTime,
            # # ScrapeWebsite,
            # # SearchWeb,
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
    asyncio.run(start_client())
