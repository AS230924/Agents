"""
PM OS Router - Intent classification to route messages to the right agent
"""

import anthropic
from agents import AGENTS, Agent


ROUTER_SYSTEM_PROMPT = """You are an intent classifier for a PM (Product Manager) assistant system.

Your job is to analyze user messages and determine which specialized agent should handle the request.

Available agents and when to use them:

1. **framer** - Use for:
   - Vague or unclear problems that need definition
   - "Users are doing X but not Y" type observations
   - Symptoms without clear root causes
   - When someone says "something is wrong" but can't articulate what
   - Discovery and problem exploration

2. **strategist** - Use for:
   - Prioritization decisions between options
   - "Should we do X or Y?" questions
   - Resource allocation questions
   - Trade-off analysis
   - Roadmap decisions
   - Comparing features, initiatives, or strategies

3. **aligner** - Use for:
   - Stakeholder management and preparation
   - Meeting prep with executives, leadership, or cross-functional partners
   - Political navigation
   - Getting buy-in or alignment
   - Conflict resolution between teams
   - Mentions of specific people or meetings

4. **executor** - Use for:
   - Shipping and execution focus
   - MVP scoping
   - Cutting features or reducing scope
   - Launch checklists
   - "How do we ship this?" questions
   - Getting things done quickly

5. **narrator** - Use for:
   - Executive communication
   - Writing updates, emails, or announcements
   - Summarizing for leadership
   - Status reports
   - When someone needs to communicate to executives
   - Requests for summaries

6. **doc_engine** - Use for:
   - Document generation requests
   - PRDs, specs, briefs
   - "Write a PRD for..." or "Create a spec for..."
   - Formal documentation needs

RESPONSE FORMAT:
Respond with ONLY the agent name in lowercase. No explanation, no punctuation, just the agent name.

Examples:
- "Users sign up but don't complete onboarding" → framer
- "Should we build AI features or focus on security?" → strategist
- "I have a meeting with my CEO tomorrow" → aligner
- "Help me cut this feature list to MVP" → executor
- "Write an exec summary of our Q1 progress" → narrator
- "Write a PRD for user onboarding" → doc_engine
"""


def classify_intent(user_message: str, api_key: str) -> str:
    """
    Classify the user's intent and return the appropriate agent name.

    Args:
        user_message: The user's input message
        api_key: Anthropic API key

    Returns:
        Agent name (lowercase string)
    """
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        system=ROUTER_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    agent_name = response.content[0].text.strip().lower()

    # Validate the agent exists
    if agent_name not in AGENTS:
        # Default to framer if classification is unclear
        return "framer"

    return agent_name


def route_message(user_message: str, api_key: str) -> tuple[str, Agent]:
    """
    Route a user message to the appropriate agent.

    Args:
        user_message: The user's input message
        api_key: Anthropic API key

    Returns:
        Tuple of (agent_name, Agent object)
    """
    agent_name = classify_intent(user_message, api_key)
    agent = AGENTS[agent_name]
    return agent_name, agent


# For testing
if __name__ == "__main__":
    import os

    test_messages = [
        "Should we prioritize AI features or enterprise security?",
        "Users are signing up but not completing onboarding",
        "I have a meeting with my CEO tomorrow about Q1 priorities",
        "Write a PRD for a new onboarding flow",
        "Help me cut this feature list to an MVP",
    ]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable to test")
    else:
        print("Testing intent classification:\n")
        for msg in test_messages:
            agent_name = classify_intent(msg, api_key)
            agent = AGENTS[agent_name]
            print(f"Message: {msg}")
            print(f"Agent: {agent.display_name}")
            print()
