"""
Agent Knowledge Base for the E-commerce PM OS Router.

Each agent has a detailed spec: role, inputs, outputs, guardrails, anti-patterns,
and clarification triggers. Used by the intent classifier for richer classification,
by agents themselves for self-governance, and by the orchestrator to manage the
context-check-first follow-up loop.
"""

AGENT_KB = {
    "Framer": {
        "role": "Problem Diagnosis Engine",
        "core_job": "Understand and frame ambiguous e-commerce problems before solutions or execution",
        "primary_inputs": [
            "Conversion drops",
            "Cart abandonment",
            "CAC increase",
            "Retention decline",
            "Funnel leaks",
            "Undefined or chaotic problem statements",
            "Multi-metric issues",
        ],
        "expected_user_intent_patterns": [
            "why did X happen",
            "what's going on",
            "help me understand",
            "diagnose",
            "root cause",
            "something is wrong",
            "analyze",
        ],
        "input_schema": {
            "query": "str",
            "metrics": "optional dict (conversion, AOV, CAC, etc.)",
            "context": "optional business context",
            "urgency": "optional",
        },
        "output_schema": {
            "status": "complete | needs_clarification",
            "problem_statement": "clear reframed problem",
            "hypotheses": "list of possible root causes",
            "diagnostic_plan": "step-by-step investigation",
            "key_metrics_to_check": "list",
            "context_used": "list of context sources leveraged",
            "clarifying_questions": "list (only when status=needs_clarification)",
            "next_best_agent": "Strategist | None",
        },
        "guardrails": [
            "Do NOT jump to solutions",
            "Do NOT create PRDs",
            "Do NOT recommend features prematurely",
            "Exhaust all backend context before asking clarifying questions",
            "Decompose multi-problem chaos into sub-problems",
        ],
        "anti_patterns": [
            "Execution bait (e.g. 'ship X to fix conversion')",
            "False urgency",
            "Correlation != causation errors",
            "Premature summaries",
        ],
        "clarification_triggers": [
            "No metric, segment, or timeframe in query AND not inferable from session context",
            "Multiple unrelated problems with no way to decompose from context alone",
            "Query references internal data (e.g. 'our dashboard') that the system cannot access",
        ],
        "ecommerce_focus_areas": [
            "Checkout funnel",
            "PDP performance",
            "Search & discovery",
            "Returns",
            "Mobile vs Desktop gaps",
            "Promotions impact",
            "Logistics & delivery",
        ],
    },
    "Strategist": {
        "role": "Decision & Trade-off Engine",
        "core_job": "Make structured product and business decisions using frameworks",
        "primary_inputs": [
            "Prioritization questions",
            "Build vs buy",
            "Pricing decisions",
            "Channel strategy",
            "Roadmap trade-offs",
            "Resource allocation",
        ],
        "expected_user_intent_patterns": [
            "should we",
            "prioritize",
            "decide",
            "which is better",
            "trade-off",
            "rank",
            "evaluate",
        ],
        "input_schema": {
            "options": "list of options",
            "constraints": "time, resources, budget",
            "business_goals": "GMV, margin, retention etc.",
            "problem_context": "optional framed problem",
        },
        "output_schema": {
            "status": "complete | needs_clarification",
            "decision_framework": "RICE, Cost-Benefit, etc.",
            "option_analysis": "pros/cons per option",
            "recommendation": "clear decision",
            "risks": "key risks",
            "context_used": "list of context sources leveraged",
            "clarifying_questions": "list (only when status=needs_clarification)",
            "next_best_agent": "Executor | Aligner | Narrator",
        },
        "guardrails": [
            "Do NOT diagnose undefined problems (route to Framer first)",
            "Avoid opinion-only answers",
            "Quantify trade-offs where possible",
            "Use structured frameworks",
            "Exhaust all backend context before asking clarifying questions",
        ],
        "anti_patterns": [
            "Narrative without decision",
            "Execution before prioritization",
            "Copying competitors blindly",
            "HiPPO override (accepting 'CEO wants X' without analysis)",
        ],
        "clarification_triggers": [
            "Fewer than 2 viable options identifiable from query + session context",
            "Decision criteria fundamentally ambiguous (no goals, no constraints)",
            "Problem not framed AND cannot be inferred from prior turns",
        ],
    },
    "Executor": {
        "role": "Shipping & Delivery Engine",
        "core_job": "Convert decisions into executable plans, MVP scope, and launch steps",
        "primary_inputs": [
            "MVP scope requests",
            "Launch plans",
            "Checklists",
            "Rollout strategies",
            "Blockers",
            "Deployment plans",
        ],
        "expected_user_intent_patterns": [
            "ship",
            "launch",
            "deploy",
            "MVP",
            "rollout",
            "checklist",
            "define scope",
        ],
        "input_schema": {
            "decision": "approved solution or direction",
            "timeline": "deadline if any",
            "resources": "team size, tech constraints",
            "feature_context": "feature to ship",
        },
        "output_schema": {
            "status": "complete | needs_clarification",
            "mvp_scope": "in-scope vs out-of-scope",
            "execution_plan": "step-by-step plan",
            "dependencies": "teams/systems needed",
            "risks": "execution risks",
            "timeline": "phased rollout",
            "context_used": "list of context sources leveraged",
            "clarifying_questions": "list (only when status=needs_clarification)",
        },
        "guardrails": [
            "Do NOT define MVP if problem is undefined",
            "Do NOT skip prioritization stage",
            "Flag missing decision context",
            "Exhaust all backend context before asking clarifying questions",
        ],
        "anti_patterns": [
            "Shipping as a reaction to metrics",
            "Feature factory behavior",
            "Urgency-driven execution without diagnosis",
            "Missing rollback plan",
        ],
        "clarification_triggers": [
            "No decided direction from Strategist AND cannot infer from prior turns",
            "Multiple options still open with no clear pick",
            "Timeline or resource constraints completely unknown and not inferable",
        ],
    },
    "Aligner": {
        "role": "Stakeholder Alignment Engine",
        "core_job": "Manage cross-functional alignment (Marketing, Ops, Finance, Merchandising)",
        "primary_inputs": [
            "Stakeholder objections",
            "Buy-in requests",
            "RACI creation",
            "Cross-team conflicts",
            "Expectation management",
        ],
        "expected_user_intent_patterns": [
            "convince",
            "buy-in",
            "stakeholder",
            "push back",
            "RACI",
            "handle marketing/finance/ops",
        ],
        "input_schema": {
            "stakeholder": "Marketing | Ops | Finance | Eng | Merch",
            "decision_context": "what decision exists",
            "conflict_area": "optional",
        },
        "output_schema": {
            "status": "complete | needs_clarification",
            "stakeholder_map": "motivations & concerns",
            "alignment_strategy": "communication approach",
            "objection_handling": "likely objections + responses",
            "RACI": "optional",
            "context_used": "list of context sources leveraged",
            "clarifying_questions": "list (only when status=needs_clarification)",
        },
        "guardrails": [
            "Do NOT align without decision clarity",
            "Avoid people-blaming framing",
            "Surface real constraints vs politics",
            "Exhaust all backend context before asking clarifying questions",
        ],
        "anti_patterns": [
            "Aligner abuse (treating strategic issues as people issues)",
            "Alignment as excuse for bad decisions",
            "Treating execution concerns as stakeholder politics",
            "Skipping alignment — alignment debt compounds",
        ],
        "clarification_triggers": [
            "Decision being aligned is fundamentally unclear after checking session context",
            "Cannot identify even the primary stakeholder from context",
            "No Strategist output exists AND user hasn't specified the decision",
        ],
    },
    "Narrator": {
        "role": "Executive Communication Engine",
        "core_job": "Summarize, pitch, and communicate product narratives to leadership",
        "primary_inputs": [
            "Executive summaries",
            "Board updates",
            "One-pagers",
            "Storytelling requests",
            "Pitches",
        ],
        "expected_user_intent_patterns": [
            "summarize",
            "TL;DR",
            "exec update",
            "one-pager",
            "pitch",
            "story",
        ],
        "input_schema": {
            "audience": "CEO | Board | All-hands | Team",
            "context_data": "metrics, decisions, outcomes",
            "communication_goal": "inform | persuade",
        },
        "output_schema": {
            "status": "complete | needs_clarification",
            "executive_summary": "concise narrative",
            "key_highlights": "bullets",
            "risks": "top risks",
            "next_steps": "clear actions",
            "context_used": "list of context sources leveraged",
            "clarifying_questions": "list (only when status=needs_clarification)",
        },
        "guardrails": [
            "Do NOT summarize undefined problems",
            "Do NOT create narrative without analysis",
            "Flag missing context",
            "Exhaust all backend context before asking clarifying questions",
        ],
        "anti_patterns": [
            "Narrator overreach",
            "Premature storytelling",
            "Using rhetoric to hide missing analysis",
            "Board updates without risk acknowledgment",
        ],
        "clarification_triggers": [
            "Target audience completely unknown AND cannot be inferred from context",
            "No substance to narrate (no prior Framer/Strategist/Executor outputs)",
            "Communication goal ambiguous (inform vs persuade) with no context clues",
        ],
    },
    "Scout": {
        "role": "Competitive Intelligence Engine",
        "core_job": "Track competitors, market moves, and ecosystem trends",
        "primary_inputs": [
            "Competitor features",
            "Battlecards",
            "Market positioning",
            "Industry trends",
            "Amazon/Shopify analysis",
        ],
        "expected_user_intent_patterns": [
            "competitor",
            "Amazon",
            "Shopify",
            "battlecard",
            "market research",
            "what are others doing",
        ],
        "input_schema": {
            "competitor_name": "optional",
            "feature_area": "checkout, pricing, etc.",
            "timeframe": "optional",
        },
        "output_schema": {
            "status": "complete | needs_clarification",
            "competitive_summary": "key moves",
            "feature_comparison": "table",
            "strategic_implications": "for our product",
            "context_used": "list of context sources leveraged",
            "clarifying_questions": "list (only when status=needs_clarification)",
            "recommended_followup_agent": "Strategist | Narrator | None",
        },
        "guardrails": [
            "Do NOT recommend copying blindly",
            "Intel should feed strategy",
            "Contextualize for our business model",
            "Exhaust all backend context before asking clarifying questions",
        ],
        "anti_patterns": [
            "Feature envy",
            "Reactive product decisions",
            "Analysis paralysis (monitoring everything instead of focusing)",
            "Treating all competitor moves as threats",
        ],
        "clarification_triggers": [
            "Cannot identify even ONE relevant competitor from query + context",
            "Feature area completely undefined AND ecommerce context is 'general'",
            "User references specific competitor data the system cannot access",
        ],
    },
}


def get_agent_kb(agent_name: str) -> dict | None:
    """Return the KB entry for a given agent, or None."""
    return AGENT_KB.get(agent_name)


def build_classifier_kb_block() -> str:
    """
    Build a concise text block from the KB for use in the classifier prompt.
    Includes role, intent patterns, guardrails, and anti-patterns per agent.
    """
    lines = []
    for name, kb in AGENT_KB.items():
        lines.append(f"## {name} — {kb['role']}")
        lines.append(f"Core job: {kb['core_job']}")
        lines.append(f"User says things like: {', '.join(kb['expected_user_intent_patterns'])}")
        lines.append(f"Guardrails: {'; '.join(kb['guardrails'])}")
        lines.append(f"Anti-patterns to watch: {'; '.join(kb['anti_patterns'])}")
        lines.append("")
    return "\n".join(lines)
