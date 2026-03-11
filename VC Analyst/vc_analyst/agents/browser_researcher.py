"""
Step 1 (Enhanced) — Browser Research Agent
Uses Playwright headless browser + DuckDuckGo web search to build a rich,
multi-source research context before LLM extraction.

Falls back gracefully to httpx + BeautifulSoup if Playwright is not installed.

Opt-in: Set USE_BROWSER_RESEARCH=1 in your .env file.
Setup:  pip install playwright duckduckgo-search && playwright install chromium
"""

from __future__ import annotations
import logging
import re
import time
from urllib.parse import urljoin, urlparse

from .base import BaseAgent
from .researcher import ResearcherAgent, _looks_like_url, NOISE_TAGS, MAX_CONTENT_CHARS
from ..core.llm_client import LLMClient
from ..models.schemas import StartupData
from ..config.prompts import BROWSER_RESEARCHER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Per-page content budget (chars)
HOMEPAGE_BUDGET   = 3_000
SUBPAGE_BUDGET    = 1_000   # /pricing, /about, /team
SEARCH_BUDGET     = 3_000   # total for all DuckDuckGo snippets
TOTAL_BUDGET      = 8_000

# Sub-pages to try for richer context
SUBPAGE_CANDIDATES = [
    "/pricing",
    "/about",
    "/team",
    "/about-us",
    "/company",
]

# Number of search results per query
SEARCH_RESULTS_PER_QUERY = 3


class BrowserResearchAgent(BaseAgent):
    """
    Enhanced researcher that uses:
    1. Playwright headless browser (handles JS-rendered SPAs)
    2. Sub-page scraping (/pricing, /about, /team)
    3. DuckDuckGo web search (funding, founders, news)

    Falls back to httpx + BeautifulSoup if Playwright is unavailable.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)
        self._playwright_available = self._check_playwright()
        self._ddgs_available = self._check_ddgs()

        if not self._playwright_available:
            logger.warning(
                "Playwright not installed. Falling back to basic httpx scraper. "
                "Run: pip install playwright && playwright install chromium"
            )
        if not self._ddgs_available:
            logger.warning(
                "duckduckgo-search not installed. Web search disabled. "
                "Run: pip install duckduckgo-search"
            )

    # ── Public Interface ──────────────────────────────────────────────────────

    def run(self, input_text: str) -> StartupData:
        """
        Args:
            input_text: A URL or plain-text description of the startup.

        Returns:
            StartupData with all extracted fields, enriched by multi-source research.
        """
        input_text = input_text.strip()

        # For plain-text descriptions, skip browser/search and use basic researcher
        if not _looks_like_url(input_text):
            logger.info("Input is a text description — using basic researcher.")
            fallback = ResearcherAgent(self._llm)
            return fallback.run(input_text)

        # Use Playwright if available, else fall back
        if self._playwright_available:
            context = self._build_rich_context(input_text)
        else:
            context = self._build_basic_context(input_text)

        user_message = f"""Research this startup from multiple sources and extract structured information:

{context}

Return the JSON object as instructed. Cross-reference all sources for accuracy."""

        raw = self._llm.call(BROWSER_RESEARCHER_SYSTEM_PROMPT, user_message)
        data = self._parse_json(raw)

        # Ensure website field is populated
        if data.get("website") in ("unknown", "", None):
            url = input_text.strip()
            if not url.startswith("http"):
                url = "https://" + url
            data["website"] = url

        return StartupData(**data)

    # ── Rich Context Builder (Playwright + Search) ────────────────────────────

    def _build_rich_context(self, url: str) -> str:
        """
        Build a multi-source research context using:
        1. Playwright-rendered homepage
        2. Key sub-pages (/pricing, /about, /team)
        3. DuckDuckGo search results (funding, founders, news)
        """
        if not url.startswith("http"):
            url = "https://" + url

        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        sections: list[str] = []
        char_budget = TOTAL_BUDGET

        # ── 1. Homepage (Playwright) ──────────────────────────────────────
        homepage_text = self._playwright_fetch(url, budget=HOMEPAGE_BUDGET)
        if homepage_text:
            sections.append(f"=== HOMEPAGE ({url}) ===\n{homepage_text}")
            char_budget -= len(homepage_text)
            logger.info(f"Homepage scraped: {len(homepage_text)} chars")
        else:
            logger.warning(f"Homepage scrape failed for {url}")

        # ── 2. Sub-pages ──────────────────────────────────────────────────
        for path in SUBPAGE_CANDIDATES:
            if char_budget < SUBPAGE_BUDGET:
                break
            subpage_url = urljoin(base_url, path)
            subpage_text = self._playwright_fetch(
                subpage_url, budget=SUBPAGE_BUDGET, quiet=True
            )
            if subpage_text and len(subpage_text) > 100:
                sections.append(f"=== {path.upper()} PAGE ===\n{subpage_text}")
                char_budget -= len(subpage_text)
                logger.info(f"Sub-page {path} scraped: {len(subpage_text)} chars")

        # ── 3. DuckDuckGo Web Search ──────────────────────────────────────
        if self._ddgs_available and char_budget > 500:
            # Derive startup name from domain for search queries
            domain = urlparse(url).netloc.replace("www.", "")
            name_guess = domain.split(".")[0].title()

            search_queries = [
                f'"{name_guess}" startup funding raised Crunchbase',
                f'"{name_guess}" founders CEO background team',
                f'"{name_guess}" AI product launch review',
            ]
            search_results = self._ddg_search(
                search_queries, budget=min(SEARCH_BUDGET, char_budget)
            )
            if search_results:
                sections.append(f"=== WEB SEARCH RESULTS ===\n{search_results}")
                logger.info(f"Search snippets: {len(search_results)} chars")

        return "\n\n".join(sections) if sections else f"Website URL: {url}\n[No content could be retrieved]"

    # ── Fallback Context Builder (httpx) ──────────────────────────────────────

    def _build_basic_context(self, url: str) -> str:
        """Fall back to simple httpx scraping when Playwright unavailable."""
        import httpx
        from bs4 import BeautifulSoup

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
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in NOISE_TAGS:
                for el in soup.find_all(tag):
                    el.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.splitlines() if l.strip()]
            text = "\n".join(lines)[:MAX_CONTENT_CHARS]
            return f"Website URL: {url}\n\nWebsite Content:\n{text}"
        except Exception as e:
            logger.warning(f"httpx fallback also failed for {url}: {e}")
            return f"Website URL: {url}\n[Unable to retrieve content]"

    # ── Playwright Helper ─────────────────────────────────────────────────────

    def _playwright_fetch(
        self, url: str, budget: int = 3_000, quiet: bool = False
    ) -> str:
        """
        Fetch a page with Playwright, wait for JS to render, return clean text.
        Returns empty string on any error.
        """
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            return ""

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                try:
                    page.goto(url, timeout=15_000, wait_until="domcontentloaded")
                    # Wait for network to be idle (JS rendered)
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except PWTimeout:
                    if not quiet:
                        logger.warning(f"Timeout loading {url}, using partial content")

                # Extract clean text from rendered DOM
                content = page.evaluate("""() => {
                    const remove = ['nav', 'footer', 'header', 'script', 'style',
                                    'noscript', 'aside', 'iframe', 'form', 'svg'];
                    remove.forEach(tag => {
                        document.querySelectorAll(tag).forEach(el => el.remove());
                    });
                    return document.body ? document.body.innerText : '';
                }""")

                browser.close()

            # Clean up whitespace
            lines = [l.strip() for l in (content or "").splitlines() if l.strip()]
            text = "\n".join(lines)
            return text[:budget]

        except Exception as e:
            if not quiet:
                logger.warning(f"Playwright fetch failed for {url}: {e}")
            return ""

    # ── DuckDuckGo Search Helper ──────────────────────────────────────────────

    def _ddg_search(self, queries: list[str], budget: int = 3_000) -> str:
        """
        Run DuckDuckGo searches and return formatted snippets.
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return ""

        all_snippets: list[str] = []
        chars_used = 0

        for query in queries:
            if chars_used >= budget:
                break
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=SEARCH_RESULTS_PER_QUERY))
                for r in results:
                    snippet = (
                        f"[{r.get('title', '')}] "
                        f"{r.get('body', '')} "
                        f"({r.get('href', '')})"
                    )
                    all_snippets.append(snippet)
                    chars_used += len(snippet)
                    if chars_used >= budget:
                        break
                # Small delay to be polite to DuckDuckGo
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed for query '{query}': {e}")

        return "\n\n".join(all_snippets)[:budget]

    # ── Availability Checks ───────────────────────────────────────────────────

    @staticmethod
    def _check_playwright() -> bool:
        """Check if playwright is installed and Chromium is available."""
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_ddgs() -> bool:
        """Check if duckduckgo-search is installed."""
        try:
            from duckduckgo_search import DDGS  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def capabilities(self) -> dict:
        """Report current capability status."""
        return {
            "playwright": self._playwright_available,
            "duckduckgo_search": self._ddgs_available,
            "mode": "full" if (self._playwright_available and self._ddgs_available)
                    else "partial" if (self._playwright_available or self._ddgs_available)
                    else "fallback (httpx)",
        }
