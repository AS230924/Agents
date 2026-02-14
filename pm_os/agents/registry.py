"""
Agent registry — maps agent names to concrete instances.

Also provides the executor that runs the full agent sequence
with KB retrieval injected at each step.
"""

import logging

from pm_os.agents.base import BaseAgent
from pm_os.agents.framer import Framer
from pm_os.agents.strategist import Strategist
from pm_os.agents.aligner import Aligner
from pm_os.agents.executor import Executor
from pm_os.agents.narrator import Narrator
from pm_os.agents.scout import Scout
from pm_os.kb.retriever import KBRetriever

log = logging.getLogger(__name__)

# Singleton agent instances
_AGENTS: dict[str, BaseAgent] = {
    "Framer": Framer(),
    "Strategist": Strategist(),
    "Aligner": Aligner(),
    "Executor": Executor(),
    "Narrator": Narrator(),
    "Scout": Scout(),
}


def get_agent(name: str) -> BaseAgent | None:
    """Look up an agent by name."""
    return _AGENTS.get(name)


def execute_sequence(
    sequence: list[str],
    query: str,
    enriched_context: dict,
    retriever: KBRetriever | None = None,
) -> list[dict]:
    """
    Execute a sequence of agents in order.

    Each agent receives the original query + enriched context.
    State updates from earlier agents carry forward into the context
    so later agents in the chain see the updated state.

    Args:
        sequence: ordered list of agent names (e.g. ["Framer", "Strategist"])
        query: original user query
        enriched_context: output of context_builder.build_context()
        retriever: KB retriever for deep agent-specific retrieval

    Returns:
        List of agent output dicts (one per agent in sequence).
    """
    results: list[dict] = []

    for agent_name in sequence:
        agent = get_agent(agent_name)
        if agent is None:
            log.warning("Unknown agent in sequence: %s", agent_name)
            results.append({
                "agent": agent_name,
                "status": "error",
                "primary_output": {"error": f"Agent '{agent_name}' not found"},
                "next_recommended_agent": None,
                "state_updates": {},
                "confidence": 0.0,
            })
            continue

        try:
            output = agent.run(query, enriched_context, retriever)
        except Exception as e:
            log.error("Agent %s failed: %s", agent_name, e)
            output = {
                "agent": agent_name,
                "status": "error",
                "primary_output": {"error": str(e)},
                "next_recommended_agent": None,
                "state_updates": {},
                "confidence": 0.0,
            }

        results.append(output)

        # Carry state updates forward into the context for the next agent
        state_updates = output.get("state_updates", {})
        if state_updates.get("problem_state"):
            enriched_context["problem_state"] = state_updates["problem_state"]
        if state_updates.get("decision_state"):
            enriched_context["decision_state"] = state_updates["decision_state"]

    return results
