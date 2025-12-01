from pydantic import BaseModel, Field


class Task(BaseModel):
    name: str = Field(..., description="The task name")
    description: str = Field(..., description="The task description")
    solution: str = Field(..., description="The task solution")
