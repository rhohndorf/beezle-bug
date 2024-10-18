from pydantic import Field

from beezle_bug.tools import Tool


class SendMessage(Tool):
    """
    Send a message to a contact.
    Use this tool only if you want to convey information to a contact.
    For example to ask a clarifying question or to inform the contact about results of your thinking.
    Don't repeat yourself!
    """

    contact: str = Field(..., description="The name of the contact to send a message to")
    message: str = Field(..., description="The message you want to send to the contact")

    def run(self, agent):

        if self.contact not in agent.contacts:
            return f"Error: {self.contact} is not a valid contact. Valid contacts are {list(agent.contacts)}"
        inbox = agent.contacts[self.contact]
        inbox.put(self.message)
        return self.message
