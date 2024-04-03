from datetime import datetime

from pydantic import Field

from tools import Tool


class Yield(Tool):
    """
    If there's nothing to do and no task task to be accomlished just yield and do nothing.
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
    Get the current date and time
    """

    def run(self):
        current_datetime = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        return current_datetime
