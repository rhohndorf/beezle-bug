from pydantic import Field

from tools import Tool


class SendMessageToUser(Tool):
    """
    Send a message to the user. Use this tool to convey information to the user.
    """

    message: str = Field(..., description="Message you want to send to the user.")

    def run(self):
        print("Assistant> " + self.message)
        return self.message
