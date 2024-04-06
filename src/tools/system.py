from datetime import datetime

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


class GetDateAndTime(Tool):
    """
    Get the current date and time
    """

    def run(self, agent):
        current_datetime = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        return current_datetime
