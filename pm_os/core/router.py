"""
Main orchestrator — wires context_builder → intent_classifier → workflow_enforcer.
"""

from pm_os.core.context_builder import build_context
from pm_os.core.intent_classifier import classify
from pm_os.core.workflow_enforcer import enforce
from pm_os.store.state_store import add_turn, update_session_state


def route(query: str, session_id: str) -> dict:
    """
    Route a user query through the full pipeline.

    Returns:
        {
            "query": str,
            "intent": str,
            "confidence": float,
            "reasoning": str,
            "sequence": list[str],
            "warning": str | None,
            "rules_applied": list[str],
            "problem_state": str,
            "decision_state": str,
            "session_id": str,
        }
    """
    # 1. Build enriched context
    ctx = build_context(query, session_id)

    # 2. Classify intent
    classification = classify(ctx)

    intent = classification["intent"]
    confidence = classification["confidence"]
    reasoning = classification["reasoning"]

    # 3. Apply workflow rules
    enforcement = enforce(
        intent=intent,
        problem_state=ctx["problem_state"],
        decision_state=ctx["decision_state"],
    )

    sequence = enforcement["sequence"]
    warning = enforcement["warning"]
    rules_applied = enforcement["rules_applied"]

    # 4. Record turn
    if sequence:
        add_turn(
            session_id=ctx["session_id"],
            query=query,
            intent=intent,
            sequence=sequence,
        )

    # 5. Update session state based on which agents are in the sequence
    _maybe_advance_state(ctx["session_id"], sequence)

    return {
        "query": query,
        "intent": intent,
        "confidence": confidence,
        "reasoning": reasoning,
        "sequence": sequence,
        "warning": warning,
        "rules_applied": rules_applied,
        "problem_state": ctx["problem_state"],
        "decision_state": ctx["decision_state"],
        "session_id": ctx["session_id"],
    }


def _maybe_advance_state(session_id: str, sequence: list[str]) -> None:
    """Advance session state when certain agents are invoked."""
    if "Framer" in sequence:
        update_session_state(session_id, problem_state="framed")
    if "Strategist" in sequence:
        update_session_state(session_id, decision_state="open")
