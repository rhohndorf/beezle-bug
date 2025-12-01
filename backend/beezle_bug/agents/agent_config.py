from pydantic import BaseModel

class AgentConfig(BaseModel):
    name: str
    model: str
    apiUrl: str
    apiKey: str
    autonomousEnabled: bool
    autonomousInterval: int
    systemTemplate: str
    tools: list[str]