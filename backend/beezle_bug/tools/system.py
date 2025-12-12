from datetime import datetime
import json

from pydantic import Field

from beezle_bug.tools import Tool


class Wait(Tool):
    """
    Just do nothing.
    This is the best tool to choose in most cases, when there is no active task to be completed.
    """

    async def run(self, agent):
        return


class Reason(Tool):
    """
    Choose this tool to take time and reason about the problem at hand.
    This is step in a larger train of thought.
    Take the information you have so far into account and think step by step.
    Try to produce new insights and intermediate results that help you solve the bigger problem later.
    Be as verbose as possible.
    """

    thought: str = Field(..., description="Your thought")

    async def run(self, agent):
        return self.thought


class SetEngagement(Tool):
    """
    Controls how active you are on the scale from 1 to 100.
    Lower values mean slower thinking and less energy consumption.
    Higher values mean faster thinking and more energy consumption.
    Choose lower values when you don't have a lot to do and higher values when you are very busy.
    """

    engagement: int = Field(..., description="")

    async def run(self, agent):
        if self.engagement < 1 or self.engagement > 100:
            return "Error: Engagement value must be in the range from 1-100"
        agent.set_engagement(self.engagement)
        return f"Engagement succesfully set to {self.engagement}."


class SelfReflect(Tool):
    """
    Choose this tool to take time to assess current situation
    What is your current goal?

    """

    situation: str = Field(..., description="A summary of the current situation")
    goal: str = Field(..., description="Your current goal")
    thought: str = Field(..., description="Your thought")

    async def run(self, agent):
        return json.dumps({"summary": self.situation, "goal": self.goal, "thought": self.thought})


class SelfCritique(Tool):
    """
    Choose this tool to take time to assess your previous actions and there success
    What can be improved

    """

    criticism: str = Field(..., description="Your self-criticism")

    async def run(self, agent):
        return self.criticism


class GetDateAndTime(Tool):
    """
    Get the current date and time
    """

    async def run(self, agent):
        current_datetime = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        return current_datetime
