import logging
from pydantic import Field
from beezle_bug.tools import Tool


class Recall(Tool):
    """
    Retrieve a list of memories that relate to the search query
    """

    query: str = Field(..., description="The query the memories are similar to")
    k: int = Field(..., description="Number of memories to retrieve")

    def run(self, agent):
        logging.debug(agent.memory_stream.memories)
        return agent.memory_stream.retrieve(self.query, self.k)


class AddWorkingMemory(Tool):
    """
    Add important information to your working memory. This information will always be accesible to you.
    You cannot add keys that already exist. If you want to change the value of an existing key, you either have to update or delete the memory first.
    """

    key: str = Field(..., description="")
    value: str = Field(..., description="")

    def run(self, agent):
        return agent.working_memory.add(self.key, self.value)


class UpdateWorkingMemory(Tool):
    """
    Update an existing memory in the working memory
    """

    key: str = Field(..., description="")
    value: str = Field(..., description="")

    def run(self, agent):
        return agent.working_memory.update(self.key, self.value)


class DeleteWorkingMemory(Tool):
    """
    Delete a memory from the working memory
    """

    key: str = Field(..., description="")

    def run(self, agent):
        return agent.working_memory.delete(self.key)
