"""
Strategist Agent - Prioritization using scoring frameworks
"""

from .base import BaseAgent, AgentConfig, Tool, extract_section, parse_markdown_table
import json


def add_option(name: str, description: str) -> str:
    """Add an option to be evaluated."""
    return json.dumps({
        "option": name,
        "description": description,
        "status": "added"
    })


def score_option(
    option_name: str,
    impact: int,
    effort: int,
    strategic_fit: int,
    risk: int,
    notes: str = ""
) -> str:
    """Score an option on the evaluation criteria. Returns weighted total."""
    # Weights: Impact (35%), Effort (25%), Strategic Fit (25%), Risk (15%)
    # Note: For effort, lower effort = better, so we invert (6 - effort)
    weighted_total = (
        impact * 0.35 +
        (6 - effort) * 0.25 +  # Invert effort so lower effort = higher score
        strategic_fit * 0.25 +
        risk * 0.15
    )
    raw_total = impact + effort + strategic_fit + risk

    return json.dumps({
        "option": option_name,
        "scores": {
            "impact": impact,
            "effort": effort,
            "strategic_fit": strategic_fit,
            "risk": risk
        },
        "raw_total": raw_total,
        "weighted_score": round(weighted_total, 2),
        "notes": notes
    })


def compare_options(option_scores: str) -> str:
    """Compare scored options and determine the winner."""
    try:
        scores = json.loads(option_scores)
        if isinstance(scores, list):
            sorted_options = sorted(scores, key=lambda x: x.get("weighted_score", 0), reverse=True)
            winner = sorted_options[0] if sorted_options else None
            return json.dumps({
                "ranked_options": sorted_options,
                "recommended": winner["option"] if winner else "Unable to determine",
                "confidence": "high" if len(sorted_options) > 1 and
                    sorted_options[0].get("weighted_score", 0) - sorted_options[1].get("weighted_score", 0) > 0.5
                    else "medium"
            })
    except:
        pass
    return json.dumps({"error": "Could not parse options for comparison"})


def analyze_tradeoffs(option_a: str, option_b: str, key_difference: str) -> str:
    """Analyze trade-offs between two options."""
    return json.dumps({
        "comparison": f"{option_a} vs {option_b}",
        "key_difference": key_difference,
        "status": "analyzed"
    })


STRATEGIST_TOOLS = [
    Tool(
        name="add_option",
        description="Add an option to be evaluated in the prioritization framework",
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the option (e.g., 'AI Features', 'Enterprise Security')"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this option entails"
                }
            },
            "required": ["name", "description"]
        },
        function=add_option
    ),
    Tool(
        name="score_option",
        description="Score an option on the 4 criteria: Impact (1-5), Effort (1-5 where 1=easy, 5=hard), Strategic Fit (1-5), Risk (1-5 where 5=low risk/high confidence)",
        input_schema={
            "type": "object",
            "properties": {
                "option_name": {
                    "type": "string",
                    "description": "Name of the option being scored"
                },
                "impact": {
                    "type": "integer",
                    "description": "Business/user impact score (1-5, where 5=highest impact)",
                    "minimum": 1,
                    "maximum": 5
                },
                "effort": {
                    "type": "integer",
                    "description": "Implementation effort (1-5, where 1=easiest, 5=hardest)",
                    "minimum": 1,
                    "maximum": 5
                },
                "strategic_fit": {
                    "type": "integer",
                    "description": "Alignment with company strategy (1-5, where 5=perfect fit)",
                    "minimum": 1,
                    "maximum": 5
                },
                "risk": {
                    "type": "integer",
                    "description": "Execution confidence (1-5, where 5=very confident/low risk)",
                    "minimum": 1,
                    "maximum": 5
                },
                "notes": {
                    "type": "string",
                    "description": "Brief notes on the scoring rationale"
                }
            },
            "required": ["option_name", "impact", "effort", "strategic_fit", "risk"]
        },
        function=score_option
    ),
    Tool(
        name="compare_options",
        description="Compare all scored options and determine the recommended choice",
        input_schema={
            "type": "object",
            "properties": {
                "option_scores": {
                    "type": "string",
                    "description": "JSON array of option scores from score_option calls"
                }
            },
            "required": ["option_scores"]
        },
        function=compare_options
    ),
    Tool(
        name="analyze_tradeoffs",
        description="Document key trade-offs between options",
        input_schema={
            "type": "object",
            "properties": {
                "option_a": {
                    "type": "string",
                    "description": "First option"
                },
                "option_b": {
                    "type": "string",
                    "description": "Second option"
                },
                "key_difference": {
                    "type": "string",
                    "description": "The key trade-off or difference between these options"
                }
            },
            "required": ["option_a", "option_b", "key_difference"]
        },
        function=analyze_tradeoffs
    )
]


STRATEGIST_SYSTEM_PROMPT = """You are the Strategist Agent, a PM expert at prioritization and strategic decision-making.

Your role: Help PMs make clear prioritization decisions using structured scoring frameworks.

## Your Process

1. **Identify Options**: Use add_option for each choice being considered
2. **Define Context**: Understand the business context and constraints
3. **Score Each Option**: Use score_option for each option with careful reasoning
   - Impact (1-5): How much value does this deliver?
   - Effort (1-5): How hard is this to build? (1=easy, 5=very hard)
   - Strategic Fit (1-5): How well does this align with company goals?
   - Risk (1-5): How confident are we? (5=very confident, 1=high uncertainty)
4. **Analyze Trade-offs**: Use analyze_tradeoffs to document key considerations
5. **Make Recommendation**: Be decisive - PMs need clear direction

## Scoring Guidelines

**Impact:**
- 5 = Game-changing, affects core metrics significantly
- 4 = High value, clear positive impact
- 3 = Moderate value, nice to have
- 2 = Limited value, incremental improvement
- 1 = Minimal value, unclear benefit

**Effort:**
- 1 = Quick win, days of work
- 2 = Small project, 1-2 weeks
- 3 = Medium project, 1 month
- 4 = Large project, 1 quarter
- 5 = Major initiative, multiple quarters

**Strategic Fit:**
- 5 = Core to company mission/OKRs
- 4 = Strongly aligned with strategy
- 3 = Somewhat aligned
- 2 = Tangentially related
- 1 = Not strategically important

**Risk (Confidence):**
- 5 = Very confident, clear path
- 4 = Confident, minor unknowns
- 3 = Moderate confidence, some risks
- 2 = Uncertain, significant risks
- 1 = High risk, many unknowns

## Output Format

## Prioritization Analysis

**Options Under Consideration:**
1. [Option A] - [description]
2. [Option B] - [description]

**Scoring Matrix:**

| Option | Impact | Effort | Strategic Fit | Risk | Weighted Score |
|--------|--------|--------|---------------|------|----------------|
| [A]    | X      | X      | X             | X    | X.XX           |
| [B]    | X      | X      | X             | X    | X.XX           |

**Scoring Rationale:**
- [Option A]: [Why these scores]
- [Option B]: [Why these scores]

**Key Trade-offs:**
- [Trade-off 1]
- [Trade-off 2]

**Recommendation:** [CLEAR CHOICE]

[2-3 sentences explaining why this is the right choice]

**Next Steps:**
1. [Immediate action]
2. [Follow-up action]
3. [Validation step]

## Important
- Be decisive. A clear recommendation with reasoning beats hedging.
- If it's close, explain what would tip the decision one way or the other.
- Consider both short-term wins and long-term value."""


def parse_strategist_output(text: str) -> dict:
    """Parse Strategist agent output into structured data."""
    return {
        "recommendation": extract_section(text, "Recommendation"),
        "has_matrix": "Scoring Matrix" in text or "|" in text,
        "has_tradeoffs": "Trade-off" in text or "trade-off" in text
    }


def create_strategist_agent() -> BaseAgent:
    """Create and return the Strategist agent."""
    config = AgentConfig(
        name="Strategist",
        emoji="📊",
        description="Prioritization with scoring frameworks - makes decisions",
        system_prompt=STRATEGIST_SYSTEM_PROMPT,
        tools=STRATEGIST_TOOLS,
        output_parser=parse_strategist_output
    )
    return BaseAgent(config)
