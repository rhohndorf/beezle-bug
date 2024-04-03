from datetime import datetime

from pydantic import Field

from tools import Tool


class Yield(Tool):
    """
    Do nothing
    """

    def run(self):
        return


class Think(Tool):
    """
    Choose this tool to take time and think about the current situation.
    Think step by step what to do next.
    """

    thought: str = Field(..., description="Your thought")

    def run(self):
        return self.thought


class GetDateAndTime(Tool):
    """
    Return the current date and time
    """

    def run(self):
        current_datetime = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        return current_datetime
