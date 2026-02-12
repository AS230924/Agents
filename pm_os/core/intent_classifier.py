"""
LLM-based intent classifier for the E-commerce PM OS Router.
Uses Claude to determine which agent the user is asking for.
"""

import json
import os
import re

import anthropic

from pm_os.config.agents import AGENTS, VALID_INTENTS

CLASSIFIER_PROMPT = """You are an intent classifier for an E-commerce PM assistant.

Given a query from a Product Manager, determine which agent they are asking for.

Agents:
- Framer: Diagnose problems (conversion drops, cart abandonment, why something happened, root cause analysis, understanding dynamics)
- Strategist: Make decisions (prioritize, choose between options, trade-offs, frameworks, resource allocation)
- Aligner: Handle stakeholders (get buy-in, manage objections, RACI, navigate conversations, prepare talking points)
- Executor: Ship things (MVP scope, launch checklist, blockers, rollout plans, deploy)
- Narrator: Communicate (summaries, pitches, exec updates, stories about completed work)
- Scout: Competitive intel (what competitors are doing, battlecards, market positioning)

IMPORTANT RULES:
1. Classify based on what the user is ASKING FOR, not what they SHOULD do.
2. If they ask "Ship a feature to fix conversion" - they're asking for Executor, even if they should use Framer first.
3. If the query mentions a PROBLEM that hasn't been diagnosed (metrics dropping, things broken, "don't understand why"), lean toward Framer.
4. If the query is not related to e-commerce product management at all, respond with intent "None".
5. Empty or meaningless queries should get intent "Framer" with low confidence.

Query: {query}

Respond ONLY with valid JSON (no markdown fences):
{{
    "intent": "<agent name or None>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
}}"""


def classify(enriched_query: dict) -> dict:
    """
    Classify intent using the Claude API.

    Args:
        enriched_query: dict with at least a "query" key.

    Returns:
        {"intent": str, "confidence": float, "reasoning": str}
    """
    query = enriched_query.get("query", "").strip()

    # Handle empty / very short queries
    if not query:
        return {
            "intent": "Framer",
            "confidence": 0.3,
            "reasoning": "Empty query — defaulting to Framer for clarification.",
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)

    prompt = CLASSIFIER_PROMPT.format(query=query)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    parsed = _parse_response(raw)
    return parsed


def _parse_response(raw: str) -> dict:
    """Parse the LLM JSON response, with fallback."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "intent": "Framer",
            "confidence": 0.3,
            "reasoning": f"Failed to parse classifier response: {raw[:120]}",
        }

    intent = data.get("intent", "Framer")
    if intent not in VALID_INTENTS and intent != "None":
        intent = "Framer"

    confidence = data.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    reasoning = data.get("reasoning", "")

    return {
        "intent": intent,
        "confidence": confidence,
        "reasoning": reasoning,
    }
