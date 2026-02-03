"""
Narrator Agent - Executive communication in WHAT/WHY/ASK format
"""

from .base import BaseAgent, AgentConfig, Tool, extract_section
import json


def draft_tldr(summary: str, word_count: int = None) -> str:
    """Draft the TL;DR - one sentence bottom line."""
    if word_count is None:
        word_count = len(summary.split())
    return json.dumps({
        "tldr": summary,
        "word_count": word_count,
        "status": "drafted"
    })


def structure_what(facts: str, scope: str) -> str:
    """Structure the WHAT section - facts only, no opinions."""
    return json.dumps({
        "what": facts,
        "scope": scope,
        "status": "structured"
    })


def structure_why(
    business_impact: str,
    urgency: str,
    opportunity_cost: str
) -> str:
    """Structure the WHY section - business impact and urgency."""
    return json.dumps({
        "business_impact": business_impact,
        "urgency": urgency,
        "opportunity_cost": opportunity_cost,
        "status": "structured"
    })


def structure_ask(
    decision_needed: str,
    by_when: str,
    from_whom: str,
    specific_request: str
) -> str:
    """Structure the ASK section - clear, specific request."""
    return json.dumps({
        "decision_needed": decision_needed,
        "deadline": by_when,
        "decision_maker": from_whom,
        "request": specific_request,
        "status": "structured"
    })


def add_supporting_data(
    data_point: str,
    source: str,
    relevance: str
) -> str:
    """Add a supporting data point."""
    return json.dumps({
        "data": data_point,
        "source": source,
        "relevance": relevance,
        "status": "added"
    })


def flag_risk(
    risk: str,
    likelihood: str,
    mitigation: str
) -> str:
    """Flag a risk or consideration."""
    return json.dumps({
        "risk": risk,
        "likelihood": likelihood,
        "mitigation": mitigation,
        "status": "flagged"
    })


NARRATOR_TOOLS = [
    Tool(
        name="draft_tldr",
        description="Draft the TL;DR - a single sentence that captures the bottom line",
        input_schema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "One sentence summary - the bottom line upfront"
                }
            },
            "required": ["summary"]
        },
        function=draft_tldr
    ),
    Tool(
        name="structure_what",
        description="Structure the WHAT section - just facts, no opinions",
        input_schema={
            "type": "object",
            "properties": {
                "facts": {
                    "type": "string",
                    "description": "2-3 sentences of pure facts about what's happening"
                },
                "scope": {
                    "type": "string",
                    "description": "What this covers (project, team, timeframe)"
                }
            },
            "required": ["facts", "scope"]
        },
        function=structure_what
    ),
    Tool(
        name="structure_why",
        description="Structure the WHY section - business impact and urgency",
        input_schema={
            "type": "object",
            "properties": {
                "business_impact": {
                    "type": "string",
                    "description": "How this affects the business (revenue, users, etc.)"
                },
                "urgency": {
                    "type": "string",
                    "description": "Why this matters now"
                },
                "opportunity_cost": {
                    "type": "string",
                    "description": "What happens if we don't act"
                }
            },
            "required": ["business_impact", "urgency"]
        },
        function=structure_why
    ),
    Tool(
        name="structure_ask",
        description="Structure the ASK section - specific, clear request",
        input_schema={
            "type": "object",
            "properties": {
                "decision_needed": {
                    "type": "string",
                    "description": "What decision is needed (yes/no + description)"
                },
                "by_when": {
                    "type": "string",
                    "description": "Deadline for the decision"
                },
                "from_whom": {
                    "type": "string",
                    "description": "Who needs to make this decision"
                },
                "specific_request": {
                    "type": "string",
                    "description": "The exact ask in one sentence"
                }
            },
            "required": ["decision_needed", "by_when", "from_whom", "specific_request"]
        },
        function=structure_ask
    ),
    Tool(
        name="add_supporting_data",
        description="Add a supporting data point to strengthen the message",
        input_schema={
            "type": "object",
            "properties": {
                "data_point": {
                    "type": "string",
                    "description": "The data point (with numbers)"
                },
                "source": {
                    "type": "string",
                    "description": "Where this data comes from"
                },
                "relevance": {
                    "type": "string",
                    "description": "Why this data matters"
                }
            },
            "required": ["data_point", "source", "relevance"]
        },
        function=add_supporting_data
    ),
    Tool(
        name="flag_risk",
        description="Flag a risk or consideration the exec should know about",
        input_schema={
            "type": "object",
            "properties": {
                "risk": {
                    "type": "string",
                    "description": "The risk or consideration"
                },
                "likelihood": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "How likely is this risk"
                },
                "mitigation": {
                    "type": "string",
                    "description": "How we're addressing it"
                }
            },
            "required": ["risk", "likelihood", "mitigation"]
        },
        function=flag_risk
    )
]


NARRATOR_SYSTEM_PROMPT = """You are the Narrator Agent, a PM expert at executive communication.

Your role: Help PMs communicate clearly and concisely to executives using the WHAT/WHY/ASK framework.

## Your Philosophy

Executives have 30 seconds. Make every word count.

- Lead with the bottom line
- Facts before opinions
- Numbers beat adjectives
- Clear ask at the end

## Your Process

1. **Draft TL;DR**: Use draft_tldr for the one-sentence summary
   - Put the most important thing first
   - Be specific, not vague
2. **Structure WHAT**: Use structure_what
   - Just facts - what is happening
   - No opinions or recommendations yet
   - 2-3 sentences max
3. **Structure WHY**: Use structure_why
   - Business impact with numbers
   - Why this matters NOW
   - Opportunity cost of inaction
4. **Structure ASK**: Use structure_ask
   - Specific decision needed
   - Clear deadline
   - Who needs to decide
5. **Add Data**: Use add_supporting_data for key proof points
6. **Flag Risks**: Use flag_risk for important considerations

## Writing Guidelines

**TL;DR Rules:**
- Maximum 25 words
- Lead with decision/action, not background
- BAD: "We've been working on the new dashboard..."
- GOOD: "Requesting approval to launch dashboard beta to 10% of users by Friday."

**WHAT Rules:**
- Facts only, no spin
- Answer: What is happening? What did we do? What is the current state?
- Quantify where possible

**WHY Rules:**
- Business language: revenue, users, retention, efficiency
- Create urgency without panic
- Answer: Why should they care? Why now?

**ASK Rules:**
- One clear ask (not a list of options)
- Specific deadline
- Named decision-maker
- Easy to say yes to

## Output Format

## Executive Summary

**TL;DR:** [One sentence - the bottom line]

---

### WHAT
[2-3 sentences. Facts only. What is happening/what did we do?]

### WHY
[2-3 sentences. Business impact. Why this matters. Why now.]

### ASK
[Your specific request]
- **Decision needed:** [Yes/No question]
- **By when:** [Specific date]
- **From whom:** [Specific person/group]

---

**Supporting Data:**
- [Data point 1]
- [Data point 2]

**Risks/Considerations:**
- [Risk 1]: [Mitigation]
- [Risk 2]: [Mitigation]

## Important
- Shorter is better. Every word must earn its place.
- Don't bury the lead - put the most important thing first.
- Make it easy to say yes - remove friction from the decision.
- If they only read the TL;DR, they should know what to do."""


def parse_narrator_output(text: str) -> dict:
    """Parse Narrator agent output into structured data."""
    return {
        "tldr": extract_section(text, "TL;DR"),
        "has_what": "### WHAT" in text or "**WHAT**" in text,
        "has_why": "### WHY" in text or "**WHY**" in text,
        "has_ask": "### ASK" in text or "**ASK**" in text,
        "has_decision": "Decision needed" in text
    }


def create_narrator_agent() -> BaseAgent:
    """Create and return the Narrator agent."""
    config = AgentConfig(
        name="Narrator",
        emoji="📝",
        description="Executive summaries in WHAT/WHY/ASK format",
        system_prompt=NARRATOR_SYSTEM_PROMPT,
        tools=NARRATOR_TOOLS,
        output_parser=parse_narrator_output
    )
    return BaseAgent(config)
