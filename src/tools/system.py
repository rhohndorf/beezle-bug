from datetime import datetime
import json

from pydantic import Field

from tools import Tool


class Yield(Tool):
    """
    Just do nothing.
    This is the best tool to choose in most cases, when there is no active task to be completed.
    """

    def run(self, agent):
        return


class Think(Tool):
    """
    Choose this tool to take time and think about the current situation.
    Think step by step what to do next.
    """

    thought: str = Field(..., description="Your thought")

    def run(self, agent):
        return self.thought


class SelfReflect(Tool):
    """
    Choose this tool to take time to assess current situation
    What is your current goal?

    """

    situation: str = Field(..., description="A summary of the current situation")
    goal: str = Field(..., description="Your current goal")
    thought: str = Field(..., description="Your thought")

    def run(self, agent):
        return json.dumps({"summary": self.situation, "goal": self.goal, "thought": self.thought})


class SelfCritique(Tool):
    """
    Choose this tool to take time to assess your previous actions and there success
    What can be improved

    """

    criticism: str = Field(..., description="Your self-criticism")

    def run(self, agent):
        return self.criticism


class GetDateAndTime(Tool):
    """
    Get the current date and time
    """

    def run(self, agent):
        current_datetime = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        return current_datetime
