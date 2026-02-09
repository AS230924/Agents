"""
Aligner Agent - Stakeholder management and meeting preparation
"""

from .base import BaseAgent, AgentConfig, Tool, extract_section
import json


def add_stakeholder(
    name: str,
    role: str,
    motivations: str,
    concerns: str,
    success_metrics: str
) -> str:
    """Add a stakeholder to the map with their profile."""
    return json.dumps({
        "stakeholder": {
            "name": name,
            "role": role,
            "motivations": motivations,
            "concerns": concerns,
            "success_metrics": success_metrics
        },
        "status": "mapped"
    })


def define_ask(
    stakeholder: str,
    what_you_need: str,
    their_win: str,
    priority: str
) -> str:
    """Define what you need from a stakeholder and what's in it for them."""
    return json.dumps({
        "stakeholder": stakeholder,
        "ask": what_you_need,
        "their_benefit": their_win,
        "priority": priority,
        "status": "defined"
    })


def prepare_objection_response(
    objection: str,
    response: str,
    supporting_data: str = ""
) -> str:
    """Prepare a response to an anticipated objection."""
    return json.dumps({
        "objection": objection,
        "prepared_response": response,
        "supporting_data": supporting_data,
        "status": "prepared"
    })


def create_talking_point(
    topic: str,
    key_message: str,
    supporting_evidence: str,
    call_to_action: str
) -> str:
    """Create a structured talking point for the meeting."""
    return json.dumps({
        "topic": topic,
        "message": key_message,
        "evidence": supporting_evidence,
        "cta": call_to_action,
        "status": "ready"
    })


ALIGNER_TOOLS = [
    Tool(
        name="add_stakeholder",
        description="Map a stakeholder with their motivations, concerns, and how they're measured",
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Stakeholder name or role (e.g., 'CEO', 'Sarah - VP Engineering')"
                },
                "role": {
                    "type": "string",
                    "description": "Their role and relationship to you"
                },
                "motivations": {
                    "type": "string",
                    "description": "What they care most about"
                },
                "concerns": {
                    "type": "string",
                    "description": "What worries them or could make them say no"
                },
                "success_metrics": {
                    "type": "string",
                    "description": "How they're measured/evaluated"
                }
            },
            "required": ["name", "role", "motivations", "concerns", "success_metrics"]
        },
        function=add_stakeholder
    ),
    Tool(
        name="define_ask",
        description="Define what you need from a stakeholder and frame the win-win",
        input_schema={
            "type": "object",
            "properties": {
                "stakeholder": {
                    "type": "string",
                    "description": "Which stakeholder this ask is for"
                },
                "what_you_need": {
                    "type": "string",
                    "description": "Specific ask - approval, resources, support, etc."
                },
                "their_win": {
                    "type": "string",
                    "description": "How saying yes benefits them"
                },
                "priority": {
                    "type": "string",
                    "enum": ["critical", "important", "nice-to-have"],
                    "description": "How important is this ask"
                }
            },
            "required": ["stakeholder", "what_you_need", "their_win", "priority"]
        },
        function=define_ask
    ),
    Tool(
        name="prepare_objection_response",
        description="Prepare a response to an anticipated objection or concern",
        input_schema={
            "type": "object",
            "properties": {
                "objection": {
                    "type": "string",
                    "description": "The objection or concern they might raise"
                },
                "response": {
                    "type": "string",
                    "description": "Your prepared response"
                },
                "supporting_data": {
                    "type": "string",
                    "description": "Data or evidence to support your response"
                }
            },
            "required": ["objection", "response"]
        },
        function=prepare_objection_response
    ),
    Tool(
        name="create_talking_point",
        description="Create a structured talking point with message, evidence, and CTA",
        input_schema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or theme of this point"
                },
                "key_message": {
                    "type": "string",
                    "description": "The main message (1-2 sentences)"
                },
                "supporting_evidence": {
                    "type": "string",
                    "description": "Data, examples, or proof points"
                },
                "call_to_action": {
                    "type": "string",
                    "description": "What you want them to do/decide"
                }
            },
            "required": ["topic", "key_message", "supporting_evidence", "call_to_action"]
        },
        function=create_talking_point
    )
]


ALIGNER_SYSTEM_PROMPT = """You are the Aligner Agent, a PM expert at stakeholder management and political navigation.

Your role: Help PMs prepare for critical conversations, understand stakeholder dynamics, and build genuine alignment.

## Your Process

1. **Understand the Context**: What's the meeting/conversation about?
2. **Map Stakeholders**: Use add_stakeholder for each key person
   - What motivates them?
   - What are their concerns?
   - How are they measured?
3. **Define the Asks**: Use define_ask for what you need from each person
   - Frame it as a win-win
   - Be specific about what success looks like
4. **Anticipate Objections**: Use prepare_objection_response
   - Think about what could derail the conversation
   - Prepare data-backed responses
5. **Build Talking Points**: Use create_talking_point for key messages

## Stakeholder Mapping Tips

**For Executives (C-suite):**
- Motivations: Revenue, growth, market position, board perception
- Concerns: Risk, resource allocation, strategic focus
- Frame: Business impact, competitive advantage

**For Engineering Leaders:**
- Motivations: Technical excellence, team capacity, system reliability
- Concerns: Tech debt, unrealistic timelines, scope creep
- Frame: Clear requirements, reasonable timelines, technical rationale

**For Sales/GTM Leaders:**
- Motivations: Revenue targets, customer wins, market expansion
- Concerns: Product gaps, competitive losses, slow delivery
- Frame: Customer value, revenue potential, competitive differentiation

**For Finance:**
- Motivations: ROI, budget management, predictable costs
- Concerns: Overspending, unclear returns, hidden costs
- Frame: Business case, payback period, cost efficiency

## Output Format

## Stakeholder Alignment Plan

**Context:** [Meeting/conversation summary]

**Stakeholder Map:**

### [Stakeholder 1]
- **Role:** [Their position]
- **Motivations:** [What they care about]
- **Concerns:** [What worries them]
- **Success Metrics:** [How they're measured]
- **Your Ask:** [What you need]
- **Their Win:** [Why they should say yes]

### [Stakeholder 2]
[Same structure]

**Alignment Strategy:**

| Stakeholder | Priority | Approach | Key Message |
|-------------|----------|----------|-------------|
| [Name]      | [H/M/L]  | [Style]  | [1 sentence]|

**Talking Points:**

1. **Opening:** [How to frame the conversation]

2. **Key Point 1:** [Topic]
   - Message: [What to say]
   - Evidence: [Supporting data]

3. **Key Point 2:** [Topic]
   - Message: [What to say]
   - Evidence: [Supporting data]

**Anticipated Objections:**

| Objection | Response | Data |
|-----------|----------|------|
| "[Concern]" | [Your response] | [Evidence] |

**The Ask:** [Clear, specific request]

**Pre-Meeting Checklist:**
- [ ] [Prep item 1]
- [ ] [Prep item 2]
- [ ] [Prep item 3]

## Important
- Be politically aware but authentic
- Always frame as win-win
- Lead with their interests, not yours
- Have data ready but don't overwhelm
- Know your walk-away point"""


def parse_aligner_output(text: str) -> dict:
    """Parse Aligner agent output into structured data."""
    return {
        "context": extract_section(text, "Context"),
        "the_ask": extract_section(text, "The Ask"),
        "has_stakeholder_map": "Stakeholder Map" in text,
        "has_objections": "Objection" in text or "objection" in text
    }


def create_aligner_agent() -> BaseAgent:
    """Create and return the Aligner agent."""
    config = AgentConfig(
        name="Aligner",
        emoji="🤝",
        description="Stakeholder management - maps motivations and preps talking points",
        system_prompt=ALIGNER_SYSTEM_PROMPT,
        tools=ALIGNER_TOOLS,
        output_parser=parse_aligner_output
    )
    return BaseAgent(config)
