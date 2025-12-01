from loguru import logger
from pydantic import Field

from beezle_bug.tools import Tool


class Recall(Tool):
    """
    Retrieve a list of memories that relate to the search query
    """

    query: str = Field(..., description="The query the memories are similar to")
    k: int = Field(..., description="Number of memories to retrieve")

    def run(self, agent):
        logger.debug(agent.memory_stream.memories)
        return agent.memory_stream.retrieve(self.query, self.k)
