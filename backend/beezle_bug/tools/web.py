"""
Web search and browsing tools.

Supports multiple search backends:
- SearXNG (self-hosted, recommended)
- Tavily (AI-focused, requires API key)
- Brave Search (requires API key)
- DuckDuckGo (fallback, may have rate limits)
"""

import os
from loguru import logger
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from bs4 import BeautifulSoup
from pydantic import Field
import requests

from beezle_bug.tools import Tool


# =============================================================================
# Search Backends
# =============================================================================

class SearchBackend(ABC):
    """Abstract base class for search backends."""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Perform a web search and return results."""
        pass
    
    @abstractmethod
    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Perform a news search and return results."""
        pass


class SearXNGBackend(SearchBackend):
    """
    SearXNG backend - self-hosted metasearch engine.
    
    Set SEARXNG_URL environment variable to your instance URL.
    Example: http://localhost:8080 or https://searx.example.com
    """
    
    def __init__(self):
        self.base_url = os.environ.get("SEARXNG_URL", "http://localhost:8080")
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "engine": item.get("engine", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"SearXNG search error: {e}")
            raise
    
    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "news",
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "source": item.get("engine", ""),
                    "date": item.get("publishedDate", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"SearXNG news search error: {e}")
            raise


class TavilyBackend(SearchBackend):
    """
    Tavily backend - AI-focused search API.
    
    Set TAVILY_API_KEY environment variable.
    Free tier: 1000 searches/month
    """
    
    def __init__(self):
        self.api_key = os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "score": item.get("score", 0)
                })
            return results
            
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            raise
    
    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        # Tavily doesn't have a separate news endpoint, use topic filter
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "topic": "news",
                    "include_answer": False,
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "date": item.get("published_date", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"Tavily news search error: {e}")
            raise


class BraveBackend(SearchBackend):
    """
    Brave Search backend.
    
    Set BRAVE_API_KEY environment variable.
    Free tier: 2000 queries/month
    """
    
    def __init__(self):
        self.api_key = os.environ.get("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY environment variable not set")
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"X-Subscription-Token": self.api_key},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            raise
    
    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/news/search",
                params={"q": query, "count": max_results},
                headers={"X-Subscription-Token": self.api_key},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": item.get("source", ""),
                    "date": item.get("age", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"Brave news search error: {e}")
            raise


class DuckDuckGoBackend(SearchBackend):
    """
    DuckDuckGo backend using ddgs library.
    
    Note: May have rate limiting issues with heavy usage.
    Recommended only as a fallback.
    """
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
            
            results = []
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            raise
    
    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                raw_results = list(ddgs.news(query, max_results=max_results))
            
            results = []
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("body", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", "")
                })
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo news search error: {e}")
            raise


# =============================================================================
# Backend Selection
# =============================================================================

def get_search_backend() -> SearchBackend:
    """
    Get the configured search backend.
    
    Priority order:
    1. SEARXNG_URL - if set, use SearXNG
    2. TAVILY_API_KEY - if set, use Tavily
    3. BRAVE_API_KEY - if set, use Brave
    4. DuckDuckGo - fallback (may have rate limits)
    
    Set SEARCH_BACKEND to force a specific backend:
    - "searxng", "tavily", "brave", "duckduckgo"
    """
    forced_backend = os.environ.get("SEARCH_BACKEND", "").lower()
    
    if forced_backend == "searxng" or (not forced_backend and os.environ.get("SEARXNG_URL")):
        return SearXNGBackend()
    
    if forced_backend == "tavily" or (not forced_backend and os.environ.get("TAVILY_API_KEY")):
        return TavilyBackend()
    
    if forced_backend == "brave" or (not forced_backend and os.environ.get("BRAVE_API_KEY")):
        return BraveBackend()
    
    # Fallback to DuckDuckGo
    logger.warning(
        "Using DuckDuckGo as search backend (may have rate limits). "
        "Consider setting up SearXNG, Tavily, or Brave for better results."
    )
    return DuckDuckGoBackend()


# Cache the backend instance
_search_backend: Optional[SearchBackend] = None

def _get_backend() -> SearchBackend:
    global _search_backend
    if _search_backend is None:
        _search_backend = get_search_backend()
    return _search_backend


# =============================================================================
# Tools
# =============================================================================

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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(self.url, headers=headers, timeout=10)
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
            backend = _get_backend()
            results = backend.search(
                self.query,
                max_results=min(max(1, self.max_results), 25)
            )
            
            if not results:
                return f"No results found for '{self.query}'"
            
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append({
                    "rank": i,
                    **result
                })
            
            return {
                "query": self.query,
                "num_results": len(formatted_results),
                "results": formatted_results
            }
            
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
            backend = _get_backend()
            results = backend.search_news(
                self.query,
                max_results=min(max(1, self.max_results), 25)
            )
            
            if not results:
                return f"No news found for '{self.query}'"
            
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append({
                    "rank": i,
                    **result
                })
            
            return {
                "query": self.query,
                "num_results": len(formatted_results),
                "results": formatted_results
            }
            
        except Exception as e:
            logger.error(f"News search error: {e}")
            return f"Error performing news search: {str(e)}"
