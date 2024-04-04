import logging

from bs4 import BeautifulSoup
from pydantic import Field
import requests

from tools import Tool


class ScrapeWebsite(Tool):
    """
    Scrape the content of a website given its URL.
    """

    url: str = Field(
        description="The URL of the website to scrape.",
    )

    def run(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            return text
        else:
            logging.error("Failed to retrieve page:", response.status_code)
            return f"Failed to retrieve page: {response.status_code}"


class SearchWeb(Tool):
    """
    Do a web earch with DuckDuckGo
    """

    query: str = Field(
        description="the query string to search for",
    )

    def run(self):
        url = f"https://duckduckgo.com/html/?q={self.query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            search_results = soup.find_all("a", class_="result__a")
            results_string = ""
            for result in search_results:
                results_string += f"{result.get_text()} - {result['href']}\n"

            return results_string.strip()

        else:
            return "Error fetching search results"
