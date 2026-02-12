"""
Workflow rules for the E-commerce PM OS Router.
IF/THEN rules that enforce proper agent sequencing based on session state.
"""

WORKFLOW_RULES = [
    {
        "id": "RULE-01",
        "name": "Undefined problem requires Framer",
        "condition": {
            "problem_state": "undefined",
            "intent_in": ["Strategist", "Executor", "Narrator", "Aligner"],
        },
        "action": {"prepend": "Framer"},
        "warning": "Let's first understand the problem before proceeding.",
    },
    {
        "id": "RULE-02",
        "name": "No decision requires Strategist",
        "condition": {
            "decision_state": "none",
            "intent_in": ["Executor", "Narrator"],
        },
        "action": {"prepend": "Strategist"},
        "warning": "Let's decide on the approach before proceeding.",
    },
    {
        "id": "RULE-03",
        "name": "Scout feeds Strategist",
        "condition": {
            "intent": "Scout",
        },
        "action": {"append": "Strategist"},
        "warning": None,
    },
    {
        "id": "RULE-04",
        "name": "Aligner needs decision context",
        "condition": {
            "decision_state": "none",
            "intent": "Aligner",
        },
        "action": {"prepend": "Strategist"},
        "warning": "Let's clarify the decision before aligning stakeholders.",
    },
]
