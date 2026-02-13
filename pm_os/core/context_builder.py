"""
Context builder — enriches a raw query with session state from the store.

Output schema:
{
    "query": str,
    "session_id": str,
    "problem_state": "undefined" | "framed" | "validated",
    "decision_state": "none" | "open" | "decided",
    "context": {
        "ecommerce_context": "conversion | retention | checkout | ...",
        "metrics": {},
        "prior_turns": [...]
    }
}
"""

import re

from pm_os.store.state_store import (
    create_session,
    get_prior_turns,
    get_session,
    init_db,
)

# Keyword → ecommerce_context mapping
_CONTEXT_KEYWORDS = {
    "conversion": ["conversion", "convert", "checkout", "funnel", "drop-off"],
    "cart_abandonment": ["cart abandon", "abandoned cart", "cart drop"],
    "retention": ["retention", "repeat purchase", "churn", "loyalty", "returning"],
    "checkout": ["checkout", "payment", "purchase flow"],
    "search_discovery": ["search", "discovery", "finding products", "browse"],
    "pdp": ["product page", "PDP", "product detail", "bounce rate"],
    "pricing": ["price", "pricing", "AOV", "discount", "margin", "promo"],
    "cac": ["CAC", "acquisition cost", "cost per", "paid", "ad spend"],
    "mobile": ["mobile", "app", "responsive", "PWA"],
    "logistics": ["shipping", "delivery", "fulfillment", "returns", "return rate"],
    "competitive": ["competitor", "Amazon", "Shopify", "ASOS", "Zappos", "Walmart", "Shein"],
    "campaign": ["Black Friday", "holiday", "campaign", "sale", "launch"],
}

# Regex to pull out percentage or numeric metrics from the query
_METRIC_PATTERN = re.compile(
    r"(\b\d+(?:\.\d+)?%?\b)\s*(?:to\s+(\b\d+(?:\.\d+)?%?\b))?",
)


def build_context(query: str, session_id: str) -> dict:
    """
    Build an enriched query dict by fetching session state
    and inferring ecommerce context + metrics from the query text.

    Args:
        query: Raw user query string.
        session_id: Session identifier. Created if it doesn't exist.

    Returns:
        Enriched context dict matching the output schema above.
    """
    init_db()
    session = get_session(session_id)

    if session is None:
        session_id = create_session()
        session = get_session(session_id)

    prior = get_prior_turns(session_id, limit=10)
    prior_turns = [
        {
            "turn": t["turn_number"],
            "query": t["query"],
            "intent": t["intent"],
            "sequence": t["sequence"],
        }
        for t in prior
    ]

    ecommerce_context = _infer_ecommerce_context(query)
    metrics = _extract_metrics(query)

    return {
        "query": query,
        "session_id": session_id,
        "problem_state": session["problem_state"],
        "decision_state": session["decision_state"],
        "context": {
            "ecommerce_context": ecommerce_context,
            "metrics": metrics,
            "prior_turns": prior_turns,
        },
    }


def _infer_ecommerce_context(query: str) -> str:
    """Return the best-matching ecommerce context label, or 'general'."""
    q = query.lower()
    best = "general"
    best_count = 0
    for label, keywords in _CONTEXT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in q)
        if count > best_count:
            best_count = count
            best = label
    return best


def _extract_metrics(query: str) -> dict:
    """Pull numeric values out of the query as a rough metrics dict."""
    metrics: dict = {}
    matches = _METRIC_PATTERN.findall(query)
    if matches:
        numbers = []
        for groups in matches:
            for g in groups:
                if g:
                    numbers.append(g)
        if numbers:
            metrics["mentioned_values"] = numbers
    return metrics
