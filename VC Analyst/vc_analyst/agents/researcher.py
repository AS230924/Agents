"""
Step 1 — Researcher Agent
Accepts a URL or text description and returns structured StartupData.
If a URL is provided, scrapes the page content first.
"""

from __future__ import annotations
import re
import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseAgent
from ..core.llm_client import LLMClient
from ..models.schemas import StartupData
from ..config.prompts import RESEARCHER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Max characters of scraped content to send to the LLM
MAX_CONTENT_CHARS = 4_000

# Tags to strip from HTML before extracting text
NOISE_TAGS = ["nav", "footer", "header", "script", "style", "noscript", "aside",
              "iframe", "form", "button", "svg", "img"]


def _looks_like_url(text: str) -> bool:
    """Quick heuristic: starts with http(s):// or www. or is a bare domain."""
    text = text.strip()
    return bool(re.match(r"^(https?://|www\.)\S+", text, re.IGNORECASE)) or \
           bool(re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/\S*)?$", text))


def _scrape_url(url: str) -> str:
    """
    Fetch a URL and return clean text content.
    Returns empty string on failure.
    """
    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove noisy tags
    for tag in NOISE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    # Get clean text
    text = soup.get_text(separator="\n", strip=True)

    # Collapse excess blank lines
    lines = [line for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # Truncate to limit
    return text[:MAX_CONTENT_CHARS]


class ResearcherAgent(BaseAgent):
    """
    Extracts structured startup information from a URL or description.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)

    def run(self, input_text: str) -> StartupData:
        """
        Args:
            input_text: A URL or a plain-text description of a startup.

        Returns:
            StartupData with all extracted fields.
        """
        input_text = input_text.strip()
        source_label = input_text

        if _looks_like_url(input_text):
            scraped = _scrape_url(input_text)
            if scraped:
                content = f"Website URL: {input_text}\n\nWebsite Content:\n{scraped}"
                source_label = input_text
            else:
                # Scraping failed — use the URL itself as minimal context
                content = f"Website URL: {input_text}\n\n[Unable to scrape website content. Infer from URL and domain name only.]"
                logger.warning(f"Using URL-only context for {input_text}")
        else:
            # Plain text description
            content = f"Startup Description:\n{input_text}"

        user_message = f"""Analyze this startup and extract structured information:

{content}

Return the JSON object as instructed."""

        raw = self._llm.call(RESEARCHER_SYSTEM_PROMPT, user_message)
        data = self._parse_json(raw)

        # Ensure website field is populated from URL if missing
        if data.get("website") in ("unknown", "", None) and _looks_like_url(input_text):
            data["website"] = input_text.strip()
            if not data["website"].startswith("http"):
                data["website"] = "https://" + data["website"]

        return StartupData(**data)
