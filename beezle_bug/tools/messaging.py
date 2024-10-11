from pydantic import Field

from beezle_bug.tools import Tool


class SendMessage(Tool):
    """
    Send a message to a contact. Use this tool to convey information to the contact.
    """

    contact: str = Field(..., description="The name of the contact to send a message to")
    message: str = Field(..., description="The message you want to send to the contact")

    def run(self, agent):

        if self.contact not in agent.contacts:
            return
        inbox = agent.contacts[self.contact]
        inbox.put(self.message)
        return self.message
