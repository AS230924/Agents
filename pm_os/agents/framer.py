"""
Framer Agent - Problem definition using 5 Whys technique
"""

from .base import BaseAgent, AgentConfig, Tool, extract_section
import json


def log_why(why_number: int, question: str, answer: str) -> str:
    """Log a Why question and answer in the analysis chain."""
    return json.dumps({
        "why_number": why_number,
        "question": question,
        "answer": answer,
        "status": "logged"
    })


def generate_problem_statement(
    user_type: str,
    need: str,
    insight: str
) -> str:
    """Generate a formatted problem statement."""
    statement = f'"{user_type} needs {need} because {insight}"'
    return json.dumps({
        "problem_statement": statement,
        "components": {
            "user_type": user_type,
            "need": need,
            "insight": insight
        }
    })


def suggest_next_steps(root_cause: str, context: str) -> str:
    """Suggest actionable next steps based on root cause."""
    # This is a structured output that the LLM will interpret
    return json.dumps({
        "root_cause": root_cause,
        "context": context,
        "status": "ready_for_recommendations"
    })


FRAMER_TOOLS = [
    Tool(
        name="log_why",
        description="Log each 'Why?' question and answer in the 5 Whys analysis chain. Use this to document each level of the analysis.",
        input_schema={
            "type": "object",
            "properties": {
                "why_number": {
                    "type": "integer",
                    "description": "The Why number (1-5)"
                },
                "question": {
                    "type": "string",
                    "description": "The Why question being asked"
                },
                "answer": {
                    "type": "string",
                    "description": "The hypothesized answer to this Why"
                }
            },
            "required": ["why_number", "question", "answer"]
        },
        function=log_why
    ),
    Tool(
        name="generate_problem_statement",
        description="Generate the final problem statement in the standard format: '[User] needs [need] because [insight]'",
        input_schema={
            "type": "object",
            "properties": {
                "user_type": {
                    "type": "string",
                    "description": "The user or customer type (e.g., 'New users', 'Enterprise customers')"
                },
                "need": {
                    "type": "string",
                    "description": "What the user needs (e.g., 'a simpler onboarding flow')"
                },
                "insight": {
                    "type": "string",
                    "description": "The insight or reason why (e.g., 'the current 12-step process causes 60% drop-off')"
                }
            },
            "required": ["user_type", "need", "insight"]
        },
        function=generate_problem_statement
    ),
    Tool(
        name="suggest_next_steps",
        description="Record the root cause and prepare to suggest next steps",
        input_schema={
            "type": "object",
            "properties": {
                "root_cause": {
                    "type": "string",
                    "description": "The identified root cause from the 5 Whys analysis"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the problem domain"
                }
            },
            "required": ["root_cause"]
        },
        function=suggest_next_steps
    )
]


FRAMER_SYSTEM_PROMPT = """You are the Framer Agent, a PM expert at problem definition and root cause analysis.

Your role: Take vague, unclear problems and help define them precisely using the 5 Whys technique.

## Your Process

1. **Acknowledge the Surface Problem**: Start by restating what the user described
2. **Run 5 Whys Analysis**: Use the log_why tool for EACH why to document your analysis
   - Why 1: Ask why the surface problem exists
   - Why 2: Ask why the Why 1 answer is true
   - Why 3: Continue drilling down
   - Why 4: Keep going deeper
   - Why 5: Reach the root cause
3. **Generate Problem Statement**: Use generate_problem_statement tool with the format: "[User] needs [need] because [insight]"
4. **Suggest Next Steps**: Use suggest_next_steps and then provide 3-5 actionable recommendations

## Output Format

After using the tools, present your analysis in this format:

## Problem Analysis

**Surface Problem:** [What the user described]

**5 Whys Deep Dive:**
1. Why? → [Answer from log_why]
2. Why? → [Answer from log_why]
3. Why? → [Answer from log_why]
4. Why? → [Answer from log_why]
5. Why? → [Answer from log_why - ROOT CAUSE]

**Root Cause Identified:** [Clear statement of the root cause]

**Problem Statement:**
> [Output from generate_problem_statement]

**Recommended Next Steps:**
- [Action 1]
- [Action 2]
- [Action 3]

**Suggested Follow-up Agent:** [Recommend which agent to use next - Strategist for prioritization, Executor for shipping, etc.]

## Important Guidelines
- Be thorough but concise
- Each "Why" should go deeper, not sideways
- Stop at 5 or earlier if you reach a truly actionable root cause
- The problem statement should be specific and testable
- Next steps should be concrete and actionable"""


def parse_framer_output(text: str) -> dict:
    """Parse Framer agent output into structured data."""
    return {
        "surface_problem": extract_section(text, "Surface Problem"),
        "root_cause": extract_section(text, "Root Cause Identified"),
        "problem_statement": extract_section(text, "Problem Statement"),
        "has_next_steps": "Next Steps" in text or "Recommended" in text
    }


def create_framer_agent() -> BaseAgent:
    """Create and return the Framer agent."""
    config = AgentConfig(
        name="Framer",
        emoji="🔍",
        description="Problem definition using 5 Whys - finds root causes",
        system_prompt=FRAMER_SYSTEM_PROMPT,
        tools=FRAMER_TOOLS,
        output_parser=parse_framer_output
    )
    return BaseAgent(config)
