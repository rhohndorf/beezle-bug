"""
Web search and browsing tools.

Uses DuckDuckGo HTML search (no API required).
"""

from loguru import logger
from bs4 import BeautifulSoup
from pydantic import Field
from urllib.parse import unquote, parse_qs, urlparse
import requests

from beezle_bug.tools import Tool


# Shared headers for all web requests
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _extract_ddg_url(href: str) -> str:
    """Extract the actual URL from a DuckDuckGo redirect link."""
    if not href:
        return ""
    
    # DDG uses redirect URLs like: //duckduckgo.com/l/?uddg=ENCODED_URL&rut=...
    if "duckduckgo.com/l/" in href:
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    
    # Direct URL (starts with http)
    if href.startswith("http"):
        return href
    
    # Protocol-relative URL
    if href.startswith("//"):
        return "https:" + href
    
    return href

class ReadWebsite(Tool):
    """
    Retrieve the text content of a website for analysis.
    Use this to read the full content of a specific URL.
    """

    url: str = Field(
        description="The URL of the website to read.",
    )

    def run(self, agent):
        try:
            response = requests.get(self.url, headers=_HEADERS, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                
                text = soup.get_text(separator=" ", strip=True)
                
                # Truncate if too long
                if len(text) > 15000:
                    text = text[:15000] + "\n\n[Content truncated - page too long]"
                
                return text
            else:
                error_msg = f"Failed to retrieve page {self.url}: HTTP {response.status_code}"
                logger.error(error_msg)
                return error_msg
        except requests.exceptions.Timeout:
            return f"Error: Request to {self.url} timed out"
        except requests.exceptions.RequestException as e:
            return f"Error fetching {self.url}: {str(e)}"


class SearchWeb(Tool):
    """
    Search the web for information on any topic.
    Returns a list of search results with titles, URLs, and snippets.
    """

    query: str = Field(
        description="The search query string.",
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return (1-25).",
    )

    def run(self, agent):
        try:
            # POST to DuckDuckGo HTML search
            response = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": self.query},
                headers=_HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                return f"Search failed: HTTP {response.status_code}"
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all result elements
            results = soup.select(".result")
            formatted_results = []
            
            for result in results[:self.max_results]:
                # Extract title and URL from the result link
                title_elem = result.select_one(".result__a")
                snippet_elem = result.select_one(".result__snippet")
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                href = title_elem.get("href", "")
                url = _extract_ddg_url(href)
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if title and url:
                    formatted_results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            return {
                "query": self.query,
                "num_results": len(formatted_results),
                "results": formatted_results
            }
            
        except requests.exceptions.Timeout:
            return f"Error: Search request timed out"
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Error performing search: {str(e)}"


class SearchNews(Tool):
    """
    Search for recent news articles.
    Use this for current events and recent developments.
    """

    query: str = Field(
        description="The news search query string.",
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return (1-25).",
    )

    def run(self, agent):
        try:
            # POST to DuckDuckGo HTML search with news filter
            response = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": self.query, "iar": "news"},
                headers=_HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                return f"News search failed: HTTP {response.status_code}"
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all result elements
            results = soup.select(".result")
            formatted_results = []
            
            for result in results[:self.max_results]:
                # Extract title and URL from the result link
                title_elem = result.select_one(".result__a")
                snippet_elem = result.select_one(".result__snippet")
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                href = title_elem.get("href", "")
                url = _extract_ddg_url(href)
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if title and url:
                    formatted_results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            return {
                "query": self.query,
                "num_results": len(formatted_results),
                "results": formatted_results
            }
            
        except requests.exceptions.Timeout:
            return f"Error: News search request timed out"
        except Exception as e:
            logger.error(f"News search error: {e}")
            return f"Error performing news search: {str(e)}"
