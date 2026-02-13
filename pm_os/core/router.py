"""
Main orchestrator — wires context_builder -> intent_classifier -> workflow_enforcer.

Agent output schema (returned per-agent when agents actually execute):
{
    "agent": "Framer | Strategist | Executor | Aligner | Narrator | Scout",
    "status": "success | needs_clarification",
    "primary_output": {},
    "next_recommended_agent": "AgentName | null",
    "state_updates": {
        "problem_state": "undefined | framed | validated",
        "decision_state": "none | open | decided"
    },
    "confidence": 0.0
}
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
            "context": {
                "ecommerce_context": str,
                "metrics": dict,
                "prior_turns": list,
            },
            "agent_outputs": list[dict],  # placeholder for downstream agent results
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
    state_updates = _compute_state_updates(sequence)
    _apply_state_updates(ctx["session_id"], state_updates)

    # 6. Build agent_outputs placeholders for the sequence
    agent_outputs = [
        _make_agent_output_stub(agent_name, sequence, state_updates)
        for agent_name in sequence
    ]

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
        "context": ctx["context"],
        "agent_outputs": agent_outputs,
    }


def _compute_state_updates(sequence: list[str]) -> dict:
    """Determine state transitions implied by the agent sequence."""
    updates: dict = {}
    if "Framer" in sequence:
        updates["problem_state"] = "framed"
    if "Strategist" in sequence:
        updates["decision_state"] = "open"
    return updates


def _apply_state_updates(session_id: str, updates: dict) -> None:
    """Persist state transitions to the store."""
    if updates:
        update_session_state(
            session_id,
            problem_state=updates.get("problem_state"),
            decision_state=updates.get("decision_state"),
        )


def _make_agent_output_stub(
    agent_name: str,
    sequence: list[str],
    state_updates: dict,
) -> dict:
    """
    Create a stub matching the agent output schema.
    These get populated when agents actually run.
    """
    # Determine next recommended agent in sequence
    idx = sequence.index(agent_name)
    next_agent = sequence[idx + 1] if idx + 1 < len(sequence) else None

    return {
        "agent": agent_name,
        "status": "pending",
        "primary_output": {},
        "next_recommended_agent": next_agent,
        "state_updates": {
            "problem_state": state_updates.get("problem_state"),
            "decision_state": state_updates.get("decision_state"),
        },
        "confidence": 0.0,
    }
