from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import Field

from beezle_bug.tools import Tool


class Recall(Tool):
    """
    Retrieve a list of memories that relate to the search query.
    You can specify a date range to retrieve memories from.
    """

    query: str = Field(..., description="The query the memories are similar to")
    k: int = Field(..., description="Number of memories to retrieve")
    from_date: Optional[datetime] = Field(None, description="Only retrieve memories created on or after this date (ISO format)")
    to_date: Optional[datetime] = Field(None, description="Only retrieve memories created on or before this date (ISO format)")

    async def run(self, agent):
        logger.debug(f"Recalling {self.k} memories for query: {self.query}")
        return await agent.memory_stream.retrieve(self.query, self.k, self.from_date, self.to_date)
