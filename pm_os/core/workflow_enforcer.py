"""
Rules engine that enforces proper agent sequencing.
Applies workflow rules based on session state and classified intent.
"""

from pm_os.config.workflow_rules import WORKFLOW_RULES

# Canonical workflow order — agents earlier in this list run first.
_AGENT_ORDER = ["Framer", "Scout", "Strategist", "Aligner", "Executor", "Narrator"]


def enforce(intent: str, problem_state: str, decision_state: str) -> dict:
    """
    Apply workflow rules and return the enforced sequence.

    Args:
        intent: The classified agent name (e.g. "Executor").
        problem_state: "undefined" | "framed" | "validated"
        decision_state: "none" | "open" | "decided"

    Returns:
        {
            "sequence": ["Framer", "Strategist"],  # ordered agent list
            "warning": str | None,
            "rules_applied": ["RULE-01"]
        }
    """
    if intent == "None" or intent is None:
        return {
            "sequence": [],
            "warning": "This query doesn't appear to be an e-commerce PM task.",
            "rules_applied": [],
        }

    sequence = [intent]
    warning = None
    rules_applied = []

    for rule in WORKFLOW_RULES:
        if _matches(rule["condition"], intent, problem_state, decision_state):
            action = rule["action"]
            if "prepend" in action and action["prepend"] not in sequence:
                sequence.insert(0, action["prepend"])
            if "append" in action and action["append"] not in sequence:
                sequence.append(action["append"])
            if rule.get("warning") and warning is None:
                warning = rule["warning"]
            rules_applied.append(rule["id"])

    # Sort by canonical workflow order so Framer always precedes Strategist, etc.
    sequence = sorted(sequence, key=lambda a: _AGENT_ORDER.index(a) if a in _AGENT_ORDER else 99)

    return {
        "sequence": sequence,
        "warning": warning,
        "rules_applied": rules_applied,
    }


def _matches(
    condition: dict,
    intent: str,
    problem_state: str,
    decision_state: str,
) -> bool:
    """Check whether a rule condition matches the current state + intent."""
    # Check problem_state constraint
    if "problem_state" in condition:
        if problem_state != condition["problem_state"]:
            return False

    # Check decision_state constraint
    if "decision_state" in condition:
        if decision_state != condition["decision_state"]:
            return False

    # Check intent_in (intent must be one of listed values)
    if "intent_in" in condition:
        if intent not in condition["intent_in"]:
            return False

    # Check exact intent match
    if "intent" in condition:
        if intent != condition["intent"]:
            return False

    return True
