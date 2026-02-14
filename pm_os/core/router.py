"""
Main orchestrator — wires context → classify → enforce → execute.

Pipeline:
  1. Context builder  — enrich query with session state + KB
  2. Intent classifier — determine which agent the user needs
  3. Workflow enforcer — prepend/append agents per business rules
  4. Agent executor    — run agent sequence with deep KB retrieval
  5. State updater     — persist state transitions

Two modes:
  route()    — classify + enforce only (fast, no LLM agent calls)
  run()      — full pipeline including agent execution
"""

import logging

from pm_os.core.context_builder import build_context
from pm_os.core.intent_classifier import classify
from pm_os.core.workflow_enforcer import enforce
from pm_os.store.state_store import add_turn, update_session_state

log = logging.getLogger(__name__)

# Lazy-loaded KB retriever for agent execution
_retriever = None
_retriever_loaded = False


def _get_retriever():
    """Lazy-load the KB retriever singleton."""
    global _retriever, _retriever_loaded
    if not _retriever_loaded:
        try:
            from pm_os.kb.loader import load_all
            from pm_os.kb.retriever import KBRetriever

            graph, vector = load_all()
            _retriever = KBRetriever(graph, vector)
        except Exception as e:
            log.warning("KB retriever not available: %s", e)
        _retriever_loaded = True
    return _retriever


def route(query: str, session_id: str) -> dict:
    """
    Route a user query through classification + enforcement (no agent execution).

    Returns routing decision with agent_outputs as stubs.
    Use run() for full execution.
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
        "agent_outputs": [],  # stubs — use run() for real outputs
    }


def run(query: str, session_id: str) -> dict:
    """
    Full pipeline: classify → enforce → execute agents → update state.

    This is the primary entry point for production use.

    If an agent in the sequence returns status="needs_clarification",
    the pipeline halts and returns the clarifying questions to the caller.
    The response includes:
      - "needs_clarification": True
      - "clarifying_agent": which agent is asking
      - "clarifying_questions": the questions for the user
      - "pending_agents": agents that still need to run after clarification
    """
    # 1–3: Route (classify + enforce)
    result = route(query, session_id)
    sequence = result["sequence"]

    if not sequence:
        return result

    # 4. Execute agent sequence
    from pm_os.agents.registry import execute_sequence

    ctx = {
        "problem_state": result["problem_state"],
        "decision_state": result["decision_state"],
        "context": result["context"],
    }

    retriever = _get_retriever()
    agent_outputs = execute_sequence(sequence, query, ctx, retriever)

    result["agent_outputs"] = agent_outputs

    # 5. Check if any agent needs clarification
    clarifying_output = None
    pending_agents = []
    for output in agent_outputs:
        if output.get("status") == "needs_clarification":
            clarifying_output = output
        elif output.get("status") == "pending":
            pending_agents.append(output["agent"])

    if clarifying_output:
        primary = clarifying_output.get("primary_output", {})
        result["needs_clarification"] = True
        result["clarifying_agent"] = clarifying_output["agent"]
        result["clarifying_questions"] = primary.get("clarifying_questions", [])
        result["context_used"] = primary.get("context_used", [])
        result["pending_agents"] = pending_agents
        # Don't update session state — the agent hasn't completed its work
        return result

    # 6. Update state from agent outputs (use actual agent state updates,
    #    not the pre-computed ones)
    result["needs_clarification"] = False
    final_state = {}
    for output in agent_outputs:
        su = output.get("state_updates", {})
        if su.get("problem_state"):
            final_state["problem_state"] = su["problem_state"]
        if su.get("decision_state"):
            final_state["decision_state"] = su["decision_state"]

    if final_state:
        update_session_state(
            result["session_id"],
            problem_state=final_state.get("problem_state"),
            decision_state=final_state.get("decision_state"),
        )
        # Reflect in the response
        if final_state.get("problem_state"):
            result["problem_state"] = final_state["problem_state"]
        if final_state.get("decision_state"):
            result["decision_state"] = final_state["decision_state"]

    # 7. Auto-export documents (PRDs → Google Docs, User Stories → Google Sheets)
    result["exports"] = _try_export_documents(agent_outputs)

    return result


def _try_export_documents(agent_outputs: list[dict]) -> list[dict]:
    """
    Check agent outputs for exportable document types and export them.

    Looks for Executor outputs with output_type in (prd, user_stories, combined)
    and exports to Google Docs/Sheets. Failures are logged but don't break the
    pipeline — the export is best-effort.
    """
    exports = []

    for output in agent_outputs:
        if output.get("agent") != "Executor":
            continue
        if output.get("status") != "success":
            continue

        primary = output.get("primary_output", {})
        output_type = primary.get("output_type", "execution_plan")

        if output_type not in ("prd", "user_stories", "combined"):
            continue

        try:
            from pm_os.export.exporter import export_agent_output

            export_result = export_agent_output(primary)
            exports.append(export_result)

            if export_result.get("exported"):
                for doc in export_result.get("documents", []):
                    doc_type = doc.get("type", "unknown")
                    url = doc.get("doc_url") or doc.get("sheet_url", "")
                    log.info("Exported %s: %s", doc_type, url)
            else:
                log.warning(
                    "Export skipped: %s", export_result.get("error", "unknown")
                )
        except Exception as e:
            log.warning("Document export failed (non-fatal): %s", e)
            exports.append({
                "exported": False,
                "documents": [],
                "error": str(e),
            })

    return exports
