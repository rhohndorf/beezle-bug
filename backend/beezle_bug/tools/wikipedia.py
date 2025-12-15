from pydantic import Field
from beezle_bug.tools import Tool

import wikipedia


class SearchWikipedia(Tool):
    """
    Do a Wikipedia search for query
    """

    query: str = Field(..., description="the search query")
    results: int = Field(..., description="the maxmimum number of results returned")

    async def run(self, agent):
        return wikipedia.search(self.query, results=self.results)


class GetWikipediaPageSummary(Tool):
    """
    Get a plain text summary of a Wikipedia page.
    """

    query: str = Field(..., description="the search query")

    async def run(self, agent):
        return wikipedia.summary(self.query, auto_suggest=False)
