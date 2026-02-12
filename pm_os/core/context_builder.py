"""
Context builder — enriches a raw query with session state from the store.
"""

from pm_os.store.state_store import (
    create_session,
    get_prior_turns,
    get_session,
    init_db,
)


def build_context(query: str, session_id: str) -> dict:
    """
    Build an enriched query dict by fetching session state.

    Args:
        query: Raw user query string.
        session_id: Session identifier. Created if it doesn't exist.

    Returns:
        {
            "query": str,
            "problem_state": "undefined" | "framed" | "validated",
            "decision_state": "none" | "open" | "decided",
            "prior_outputs": [...],
            "session_id": str,
        }
    """
    init_db()
    session = get_session(session_id)

    if session is None:
        session_id = create_session()
        session = get_session(session_id)

    prior = get_prior_turns(session_id, limit=10)
    prior_outputs = [
        {"turn": t["turn_number"], "query": t["query"], "intent": t["intent"]}
        for t in prior
    ]

    return {
        "query": query,
        "problem_state": session["problem_state"],
        "decision_state": session["decision_state"],
        "prior_outputs": prior_outputs,
        "session_id": session_id,
    }
