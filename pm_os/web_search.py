"""
PM OS Web Search - Search for competitive intel and market research
Uses SerpAPI for reliable web search results.
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Optional
from dataclasses import dataclass


# Global API key storage (set via set_serpapi_key function)
_serpapi_key: Optional[str] = None


def set_serpapi_key(api_key: str):
    """Set the SerpAPI key for search functions."""
    global _serpapi_key
    _serpapi_key = api_key


def get_serpapi_key() -> Optional[str]:
    """Get SerpAPI key from global storage or environment."""
    global _serpapi_key
    if _serpapi_key:
        return _serpapi_key
    return os.environ.get("SERPAPI_KEY") or os.environ.get("SERP_API_KEY")


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet
        }


def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Search the web using SerpAPI (Google Search).

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of SearchResult objects
    """
    api_key = get_serpapi_key()
    if not api_key:
        return []

    try:
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": str(max_results),
            "output": "json"
        }

        url = f"https://serpapi.com/search?{urllib.parse.urlencode(params)}"

        request = urllib.request.Request(url)

        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []

        # Parse organic results from SerpAPI response
        organic_results = data.get("organic_results", [])

        for item in organic_results[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", "")
            ))

        return results

    except Exception as e:
        # Return empty results on error
        return []


def search_competitors(company_or_product: str) -> str:
    """
    Search for competitor information.

    Args:
        company_or_product: Name of company or product to research

    Returns:
        JSON string with competitor info
    """
    query = f"{company_or_product} competitors alternatives comparison"
    results = search_web(query, max_results=5)

    return json.dumps({
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results)
    })


def search_market_trends(topic: str) -> str:
    """
    Search for market trends and industry insights.

    Args:
        topic: Topic or industry to research

    Returns:
        JSON string with trend info
    """
    query = f"{topic} market trends 2024 2025 industry report"
    results = search_web(query, max_results=5)

    return json.dumps({
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results)
    })


def search_user_feedback(product: str) -> str:
    """
    Search for user feedback and reviews.

    Args:
        product: Product name to research

    Returns:
        JSON string with feedback info
    """
    query = f"{product} user reviews feedback complaints reddit"
    results = search_web(query, max_results=5)

    return json.dumps({
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results)
    })


def search_best_practices(topic: str) -> str:
    """
    Search for best practices and guides.

    Args:
        topic: Topic to find best practices for

    Returns:
        JSON string with best practices info
    """
    query = f"{topic} best practices guide how to"
    results = search_web(query, max_results=5)

    return json.dumps({
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results)
    })


def format_search_results(results_json: str) -> str:
    """Format search results for display in agent output."""
    try:
        data = json.loads(results_json)
        results = data.get("results", [])

        if not results:
            return "No results found."

        lines = [f"**Search:** {data.get('query', 'N/A')}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['title']}]({r['url']})")
            if r.get('snippet'):
                lines.append(f"   _{r['snippet'][:150]}..._\n")

        return "\n".join(lines)
    except:
        return "Error parsing search results."


# Tool definitions for agents
SEARCH_TOOLS = {
    "search_competitors": {
        "function": search_competitors,
        "description": "Search for competitors and alternatives to a company or product",
        "schema": {
            "type": "object",
            "properties": {
                "company_or_product": {
                    "type": "string",
                    "description": "Name of the company or product to research competitors for"
                }
            },
            "required": ["company_or_product"]
        }
    },
    "search_market_trends": {
        "function": search_market_trends,
        "description": "Search for market trends and industry insights on a topic",
        "schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or industry to research trends for"
                }
            },
            "required": ["topic"]
        }
    },
    "search_user_feedback": {
        "function": search_user_feedback,
        "description": "Search for user reviews, feedback, and complaints about a product",
        "schema": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "description": "Product name to find user feedback for"
                }
            },
            "required": ["product"]
        }
    },
    "search_best_practices": {
        "function": search_best_practices,
        "description": "Search for best practices and guides on a topic",
        "schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to find best practices for"
                }
            },
            "required": ["topic"]
        }
    }
}
