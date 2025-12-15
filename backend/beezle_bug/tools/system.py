from datetime import datetime

from beezle_bug.tools import Tool

class GetDateAndTime(Tool):
    """
    Get the current date and time
    """

    async def run(self, agent):
        current_datetime = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        return current_datetime
