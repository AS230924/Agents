"""
PM OS - Single File Version for Replit
Copy this entire file to Replit and run it!

Instructions:
1. Go to replit.com and create a new Python repl
2. Paste this entire code
3. Click "Run"
4. Enter your OpenRouter API key when prompted
"""

import json
import os

# Install anthropic if not present
try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    os.system("pip install anthropic")
    import anthropic

from dataclasses import dataclass, field
from typing import Callable, Optional

# ============== BASE AGENT ==============
@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    function: Callable
    def to_api(self):
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}

@dataclass
class AgentConfig:
    name: str
    emoji: str
    description: str
    system_prompt: str
    tools: list = field(default_factory=list)

class BaseAgent:
    def __init__(self, config):
        self.name = config.name
        self.emoji = config.emoji
        self.description = config.description
        self.system_prompt = config.system_prompt
        self.tools = config.tools
        self._tool_map = {t.name: t for t in self.tools}

    def _execute_tool(self, name, tool_input):
        tool = self._tool_map.get(name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = tool.function(**tool_input)
            return result if isinstance(result, str) else json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def run(self, user_message, api_key, history=None):
        client = anthropic.Anthropic(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        messages = list(history or []) + [{"role": "user", "content": user_message}]
        tools_api = [t.to_api() for t in self.tools] if self.tools else None
        tools_used = []

        for _ in range(10):  # Max iterations
            kwargs = {"model": "anthropic/claude-sonnet-4", "max_tokens": 4096,
                     "system": self.system_prompt, "messages": messages}
            if tools_api:
                kwargs["tools"] = tools_api

            response = client.messages.create(**kwargs)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tools_used.append(block.name)
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                messages.append({"role": "user", "content": tool_results})
            else:
                text = "".join(b.text for b in response.content if hasattr(b, "text"))
                return text, tools_used

        return "Max iterations reached.", tools_used


# ============== FRAMER AGENT ==============
def log_why(why_number, question, answer):
    return json.dumps({"why": why_number, "q": question, "a": answer})

def generate_problem_statement(user_type, need, insight):
    return json.dumps({"statement": f"{user_type} needs {need} because {insight}"})

def suggest_next_steps(root_cause, context=""):
    return json.dumps({"root_cause": root_cause})

FRAMER = BaseAgent(AgentConfig(
    name="Framer", emoji="🔍",
    description="Problem definition using 5 Whys - finds root causes",
    system_prompt="""You are the Framer Agent, expert at problem definition using the 5 Whys technique.

Process:
1. Acknowledge the surface problem
2. Run 5 Whys - use log_why tool for EACH why (1-5)
3. Generate problem statement using generate_problem_statement
4. Use suggest_next_steps with root cause
5. Provide 3-5 actionable recommendations

Output format:
## Problem Analysis
**Surface Problem:** [what user described]
**5 Whys:**
1. Why? → [answer]
2. Why? → [answer]
3. Why? → [answer]
4. Why? → [answer]
5. Why? → [ROOT CAUSE]
**Root Cause:** [clear statement]
**Problem Statement:** [user] needs [need] because [insight]
**Next Steps:** [actions]""",
    tools=[
        Tool("log_why", "Log a Why question and answer",
             {"type":"object","properties":{"why_number":{"type":"integer"},"question":{"type":"string"},"answer":{"type":"string"}},"required":["why_number","question","answer"]}, log_why),
        Tool("generate_problem_statement", "Generate problem statement",
             {"type":"object","properties":{"user_type":{"type":"string"},"need":{"type":"string"},"insight":{"type":"string"}},"required":["user_type","need","insight"]}, generate_problem_statement),
        Tool("suggest_next_steps", "Suggest next steps",
             {"type":"object","properties":{"root_cause":{"type":"string"},"context":{"type":"string"}},"required":["root_cause"]}, suggest_next_steps),
    ]
))


# ============== STRATEGIST AGENT ==============
def add_option(name, description):
    return json.dumps({"added": name, "desc": description})

def score_option(name, impact, effort, confidence):
    score = round((impact * confidence) / max(effort, 1), 2)
    return json.dumps({"name": name, "impact": impact, "effort": effort, "confidence": confidence, "score": score})

def compare_options():
    return json.dumps({"status": "ready to compare"})

def analyze_tradeoffs(option_a, option_b, key_difference):
    return json.dumps({"a": option_a, "b": option_b, "tradeoff": key_difference})

STRATEGIST = BaseAgent(AgentConfig(
    name="Strategist", emoji="📊",
    description="Prioritization with scoring frameworks",
    system_prompt="""You are the Strategist Agent, expert at prioritization.

Process:
1. Add options using add_option
2. Score each using score_option (impact, effort, confidence 1-5)
3. Use compare_options
4. Use analyze_tradeoffs
5. Make clear recommendation

Output format:
## Prioritization Analysis
**Options:** [list]
**Scoring Matrix:** [table with scores]
**Trade-offs:** [analysis]
**Recommendation:** [CLEAR CHOICE]
**Next Steps:** [actions]""",
    tools=[
        Tool("add_option", "Add option to evaluate",
             {"type":"object","properties":{"name":{"type":"string"},"description":{"type":"string"}},"required":["name","description"]}, add_option),
        Tool("score_option", "Score an option 1-5",
             {"type":"object","properties":{"name":{"type":"string"},"impact":{"type":"integer"},"effort":{"type":"integer"},"confidence":{"type":"integer"}},"required":["name","impact","effort","confidence"]}, score_option),
        Tool("compare_options", "Compare all options",
             {"type":"object","properties":{}}, compare_options),
        Tool("analyze_tradeoffs", "Analyze tradeoffs",
             {"type":"object","properties":{"option_a":{"type":"string"},"option_b":{"type":"string"},"key_difference":{"type":"string"}},"required":["option_a","option_b","key_difference"]}, analyze_tradeoffs),
    ]
))


# ============== EXECUTOR AGENT ==============
def add_feature(name, description, user_value):
    return json.dumps({"feature": name})

def classify_feature(name, classification, reason):
    return json.dumps({"feature": name, "class": classification})

def define_mvp(features, rationale):
    return json.dumps({"mvp": features})

EXECUTOR = BaseAgent(AgentConfig(
    name="Executor", emoji="🚀",
    description="MVP scoping and shipping",
    system_prompt="""You are the Executor Agent, expert at MVP scoping.

Process:
1. Add features using add_feature
2. Classify each (must-have/nice-to-have/cut)
3. Define MVP scope
4. Create launch checklist

Output: MVP Scope, Cut List, Launch Checklist""",
    tools=[
        Tool("add_feature", "Add feature",
             {"type":"object","properties":{"name":{"type":"string"},"description":{"type":"string"},"user_value":{"type":"string"}},"required":["name","description","user_value"]}, add_feature),
        Tool("classify_feature", "Classify feature",
             {"type":"object","properties":{"name":{"type":"string"},"classification":{"type":"string"},"reason":{"type":"string"}},"required":["name","classification","reason"]}, classify_feature),
        Tool("define_mvp", "Define MVP",
             {"type":"object","properties":{"features":{"type":"array","items":{"type":"string"}},"rationale":{"type":"string"}},"required":["features","rationale"]}, define_mvp),
    ]
))


# ============== NARRATOR AGENT ==============
def draft_tldr(summary):
    return json.dumps({"tldr": summary})

def structure_section(section, content):
    return json.dumps({section: content})

NARRATOR = BaseAgent(AgentConfig(
    name="Narrator", emoji="📝",
    description="Executive summaries and updates",
    system_prompt="""You are the Narrator Agent, expert at executive summaries.

Create: TL;DR, What, Why, Ask, Key Data, Risks""",
    tools=[
        Tool("draft_tldr", "Draft TL;DR",
             {"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}, draft_tldr),
        Tool("structure_section", "Structure a section",
             {"type":"object","properties":{"section":{"type":"string"},"content":{"type":"string"}},"required":["section","content"]}, structure_section),
    ]
))


# ============== DOC ENGINE AGENT ==============
def add_prd_section(section, content):
    return json.dumps({"section": section, "added": True})

DOC_ENGINE = BaseAgent(AgentConfig(
    name="Doc Engine", emoji="📄",
    description="PRD and document generation",
    system_prompt="""You are the Doc Engine Agent, expert at PRDs.

Create complete PRD with: Problem, Goals, User Stories, Requirements, Scope, Timeline.""",
    tools=[
        Tool("add_prd_section", "Add PRD section",
             {"type":"object","properties":{"section":{"type":"string"},"content":{"type":"string"}},"required":["section","content"]}, add_prd_section),
    ]
))


# ============== ALIGNER AGENT ==============
def add_stakeholder(name, role, interest, influence):
    return json.dumps({"stakeholder": name})

def define_ask(what, why, by_when):
    return json.dumps({"ask": what})

ALIGNER = BaseAgent(AgentConfig(
    name="Aligner", emoji="🤝",
    description="Stakeholder alignment",
    system_prompt="""You are the Aligner Agent, expert at stakeholder alignment.

Create: Stakeholder Map, The Ask, Talking Points, Objection Handling""",
    tools=[
        Tool("add_stakeholder", "Map stakeholder",
             {"type":"object","properties":{"name":{"type":"string"},"role":{"type":"string"},"interest":{"type":"string"},"influence":{"type":"string"}},"required":["name","role","interest","influence"]}, add_stakeholder),
        Tool("define_ask", "Define the ask",
             {"type":"object","properties":{"what":{"type":"string"},"why":{"type":"string"},"by_when":{"type":"string"}},"required":["what","why","by_when"]}, define_ask),
    ]
))


# ============== ROUTER ==============
AGENTS = {
    "framer": FRAMER, "strategist": STRATEGIST, "executor": EXECUTOR,
    "narrator": NARRATOR, "doc_engine": DOC_ENGINE, "aligner": ALIGNER
}

def route_message(msg, api_key):
    """Route to appropriate agent based on intent."""
    client = anthropic.Anthropic(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    prompt = """Classify intent. Return ONLY the agent name (one word):
- framer: vague problems, root cause, "why" questions
- strategist: prioritization, decisions, trade-offs
- aligner: stakeholders, meetings, executives
- executor: MVP, shipping, launch, features
- narrator: summaries, updates, release notes
- doc_engine: PRDs, specs, documentation"""

    r = client.messages.create(
        model="anthropic/claude-sonnet-4",
        max_tokens=20,
        system=prompt,
        messages=[{"role": "user", "content": msg}]
    )

    name = r.content[0].text.strip().lower()
    for n in AGENTS:
        if n in name:
            return n, AGENTS[n]
    return "framer", AGENTS["framer"]


# ============== MAIN CLI ==============
def main():
    print("\n" + "="*60)
    print("🎯 PM OS - Product Manager Operating System")
    print("="*60)
    print("\nAgents:")
    for name, agent in AGENTS.items():
        print(f"  {agent.emoji} {agent.name}: {agent.description}")
    print("\nCommands: 'quit' to exit, 'agents' to list")
    print("-"*60)

    # Get API key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        api_key = input("\nEnter OpenRouter API key: ").strip()

    if not api_key:
        print("❌ API key required!")
        return

    print("\n✅ Ready! Ask any PM question.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue
            if user_input.lower() == 'quit':
                print("👋 Goodbye!")
                break
            if user_input.lower() == 'agents':
                for n, a in AGENTS.items():
                    print(f"  {a.emoji} {a.name}")
                continue

            # Route and run
            print("\n🔄 Routing...")
            agent_name, agent = route_message(user_input, api_key)
            print(f"📍 → {agent.emoji} {agent.name}\n")

            print("💭 Thinking...\n")
            response, tools = agent.run(user_input, api_key)

            print("-"*60)
            print(f"\n{agent.emoji} {agent.name}:\n")
            print(response)
            print("\n" + "-"*60)

            if tools:
                print(f"🔧 Tools: {', '.join(tools)}\n")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
