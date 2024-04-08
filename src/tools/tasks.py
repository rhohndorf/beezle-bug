from typing import List
from pydantic import Field

from tools import Tool


class MakePlan(Tool):
    """
    Make a multi-step plan how to achieve the goal.
    Use this whenever you are not sure how to achieve a goal in one step.
    """

    goal: str = Field(..., description="The original task that needs to be decomposed into subtasks.")
    plan: List[str] = Field(..., description="The list of step to achieve the goal")

    def run(self, agent):
        return self.model_dump_json()


class AssessTaskSolution(Tool):
    """
    bla
    """

    pass
