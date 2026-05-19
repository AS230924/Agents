"""Lightweight DuckDuckGo search wrapper.

Requires: pip install duckduckgo-search
Falls back to empty list if package not installed (agents degrade gracefully).
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Run a DuckDuckGo search and return list of dict results."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except ImportError:
        logger.debug("duckduckgo_search not installed — skipping web search")
        return []
    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")
        return []


def format_search_results(results: list[dict], max_chars: int = 2000) -> str:
    """Format search results as compact text for LLM context."""
    if not results:
        return "(no web search results available)"

    lines: list[str] = []
    total = 0
    for r in results:
        snippet = f"[{r.get('title', '')}] {r.get('body', '')} ({r.get('href', '')})"
        if total + len(snippet) > max_chars:
            break
        lines.append(snippet)
        total += len(snippet)
    return "\n".join(lines)
