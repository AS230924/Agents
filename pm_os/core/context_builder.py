"""
Context builder — enriches a raw query with session state from the store
and relevant knowledge from the KB (vector + graph).

Output schema:
{
    "query": str,
    "session_id": str,
    "problem_state": "undefined" | "framed" | "validated",
    "decision_state": "none" | "open" | "decided",
    "context": {
        "ecommerce_context": "conversion | retention | checkout | ...",
        "metrics": {},
        "prior_turns": [...],
        "kb_summary": str,        # LLM-ready knowledge context
        "kb_vector_hits": [...],   # raw vector results
        "kb_graph_context": {},    # raw graph traversal results
    }
}
"""

import logging
import re

from pm_os.store.state_store import (
    create_session,
    get_prior_turns,
    get_session,
    init_db,
)

log = logging.getLogger(__name__)

# Lazy-loaded KB singletons (initialized on first use)
_kb_retriever = None
_kb_loaded = False

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

    # KB retrieval (agent-agnostic at this stage; agent-specific retrieval
    # happens later once intent is classified — we do a broad Framer-level
    # retrieval here to enrich the classifier prompt)
    kb_summary, kb_vector_hits, kb_graph_context = _retrieve_kb(
        query, ecommerce_context
    )

    return {
        "query": query,
        "session_id": session_id,
        "problem_state": session["problem_state"],
        "decision_state": session["decision_state"],
        "context": {
            "ecommerce_context": ecommerce_context,
            "metrics": metrics,
            "prior_turns": prior_turns,
            "kb_summary": kb_summary,
            "kb_vector_hits": kb_vector_hits,
            "kb_graph_context": kb_graph_context,
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


def _retrieve_kb(
    query: str, ecommerce_context: str
) -> tuple[str, list[dict], dict]:
    """
    Retrieve knowledge context from the KB stores.
    Returns (summary, vector_hits, graph_context).
    Falls back gracefully if KB is not loaded or dependencies missing.
    """
    global _kb_retriever, _kb_loaded

    if not _kb_loaded:
        try:
            from pm_os.kb.loader import load_all
            from pm_os.kb.retriever import KBRetriever

            graph, vector = load_all()
            _kb_retriever = KBRetriever(graph, vector)
            _kb_loaded = True
        except Exception as e:
            log.warning("KB not available: %s", e)
            _kb_loaded = True  # don't retry every call
            return "", [], {}

    if _kb_retriever is None:
        return "", [], {}

    try:
        # Use Framer as default agent for broad context retrieval
        result = _kb_retriever.retrieve(
            agent_name="Framer",
            query=query,
            ecommerce_context=ecommerce_context,
            n_results=3,
        )
        return (
            result.get("summary", ""),
            result.get("vector_results", []),
            result.get("graph_context", {}),
        )
    except Exception as e:
        log.warning("KB retrieval failed: %s", e)
        return "", [], {}
