DEFAULT_DATA_DIR = "/app/data"
AGENT_SUBFOLDER = "agents"
TEMPLATE_SUBFOLDER = "templates"
DEFAULT_CONFIG = {
    "name": "Beezle Bug",
    "model": "local-model",
    "apiUrl": "http://127.0.0.1:1234/v1",
    "apiKey": "",
    "temperature": 0.7,
    "autonomousEnabled": False,
    "autonomousInterval": 30,
    "systemTemplate": "system_messages/agent"
}

DEFAULT_MSG_BUFFER_SIZE = 100