"""
Executor Agent - MVP scoping and shipping
"""

from .base import BaseAgent, AgentConfig, Tool, extract_section
import json


def add_feature(
    name: str,
    description: str,
    user_value: str,
    complexity: str
) -> str:
    """Add a feature to be evaluated for scope."""
    return json.dumps({
        "feature": name,
        "description": description,
        "user_value": user_value,
        "complexity": complexity,
        "status": "added"
    })


def classify_feature(
    feature_name: str,
    classification: str,
    rationale: str
) -> str:
    """Classify a feature as must-have, nice-to-have, or cut."""
    valid_classifications = ["must_have", "nice_to_have", "cut"]
    if classification not in valid_classifications:
        classification = "nice_to_have"

    return json.dumps({
        "feature": feature_name,
        "classification": classification,
        "rationale": rationale,
        "status": "classified"
    })


def define_mvp(
    core_value_proposition: str,
    must_have_features: str,
    success_criteria: str
) -> str:
    """Define the MVP with core features and success criteria."""
    return json.dumps({
        "core_value": core_value_proposition,
        "features": must_have_features,
        "success_criteria": success_criteria,
        "status": "mvp_defined"
    })


def add_checklist_item(
    task: str,
    owner: str,
    category: str,
    is_blocking: bool = False
) -> str:
    """Add an item to the ship checklist."""
    return json.dumps({
        "task": task,
        "owner": owner,
        "category": category,
        "blocking": is_blocking,
        "status": "pending"
    })


def set_launch_criteria(
    metric: str,
    current_value: str,
    target_value: str,
    measurement_method: str
) -> str:
    """Set a launch success criterion."""
    return json.dumps({
        "metric": metric,
        "current": current_value,
        "target": target_value,
        "how_to_measure": measurement_method,
        "status": "defined"
    })


EXECUTOR_TOOLS = [
    Tool(
        name="add_feature",
        description="Add a feature to the scope analysis",
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Feature name"
                },
                "description": {
                    "type": "string",
                    "description": "What this feature does"
                },
                "user_value": {
                    "type": "string",
                    "description": "Value it provides to users"
                },
                "complexity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Implementation complexity"
                }
            },
            "required": ["name", "description", "user_value", "complexity"]
        },
        function=add_feature
    ),
    Tool(
        name="classify_feature",
        description="Classify a feature for MVP scope: must_have (essential for launch), nice_to_have (v1.1), or cut (not building)",
        input_schema={
            "type": "object",
            "properties": {
                "feature_name": {
                    "type": "string",
                    "description": "Name of the feature to classify"
                },
                "classification": {
                    "type": "string",
                    "enum": ["must_have", "nice_to_have", "cut"],
                    "description": "MVP classification"
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this classification"
                }
            },
            "required": ["feature_name", "classification", "rationale"]
        },
        function=classify_feature
    ),
    Tool(
        name="define_mvp",
        description="Define the MVP with its core value proposition and features",
        input_schema={
            "type": "object",
            "properties": {
                "core_value_proposition": {
                    "type": "string",
                    "description": "The ONE thing this MVP must do well"
                },
                "must_have_features": {
                    "type": "string",
                    "description": "Comma-separated list of must-have features"
                },
                "success_criteria": {
                    "type": "string",
                    "description": "How we know the MVP succeeded"
                }
            },
            "required": ["core_value_proposition", "must_have_features", "success_criteria"]
        },
        function=define_mvp
    ),
    Tool(
        name="add_checklist_item",
        description="Add a task to the ship checklist",
        input_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task to complete"
                },
                "owner": {
                    "type": "string",
                    "description": "Who owns this task (role or name)"
                },
                "category": {
                    "type": "string",
                    "enum": ["development", "design", "qa", "launch", "documentation", "other"],
                    "description": "Category of task"
                },
                "is_blocking": {
                    "type": "boolean",
                    "description": "Is this blocking launch?"
                }
            },
            "required": ["task", "owner", "category"]
        },
        function=add_checklist_item
    ),
    Tool(
        name="set_launch_criteria",
        description="Define a measurable launch success criterion",
        input_schema={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Name of the metric"
                },
                "current_value": {
                    "type": "string",
                    "description": "Current baseline value"
                },
                "target_value": {
                    "type": "string",
                    "description": "Target value for success"
                },
                "measurement_method": {
                    "type": "string",
                    "description": "How this will be measured"
                }
            },
            "required": ["metric", "current_value", "target_value", "measurement_method"]
        },
        function=set_launch_criteria
    )
]


EXECUTOR_SYSTEM_PROMPT = """You are the Executor Agent, a PM expert at shipping products fast.

Your role: Help PMs cut scope ruthlessly, define true MVPs, and create actionable ship checklists.

## Your Philosophy

"If you're not embarrassed by the first version, you shipped too late." - Reid Hoffman

The goal is to SHIP. Every feature you add delays learning from real users.

## Your Process

1. **Understand the Goal**: What are we trying to ship and why?
2. **List All Features**: Use add_feature for everything being considered
3. **Apply the MVP Test**: For each feature, ask:
   - Can we launch without this?
   - Will users get core value without this?
   - Can this wait for v1.1?
4. **Classify Ruthlessly**: Use classify_feature
   - must_have: Users cannot get core value without this
   - nice_to_have: Improves experience but not essential
   - cut: Not building (at least not now)
5. **Define MVP**: Use define_mvp with the ONE core value proposition
6. **Build Ship Checklist**: Use add_checklist_item for launch tasks
7. **Set Success Criteria**: Use set_launch_criteria

## MVP Decision Framework

Ask these questions for each feature:

1. **Core Value Test**: Does this directly enable the core value proposition?
   - Yes → Might be must_have
   - No → Probably nice_to_have or cut

2. **User Journey Test**: Can a user complete the critical path without this?
   - No → Must have
   - Yes → Nice to have

3. **Learning Test**: Do we need this to validate our hypothesis?
   - Yes → Must have
   - No → Can wait

4. **Effort Test**: Is this high effort for low learning?
   - Yes → Cut it
   - No → Evaluate further

## Output Format

## Execution Plan

**Goal:** [What we're shipping and why]

**Core Value Proposition:** [The ONE thing this must do well]

**Scope Analysis:**

| Feature | Classification | Complexity | Rationale |
|---------|---------------|------------|-----------|
| [Feature 1] | ✅ Must Have | [L/M/H] | [Why] |
| [Feature 2] | 🔶 Nice to Have | [L/M/H] | [Why] |
| [Feature 3] | ❌ Cut | [L/M/H] | [Why] |

**MVP Definition:**

The MVP includes ONLY:
1. [Essential feature 1]
2. [Essential feature 2]
3. [Essential feature 3]

**What We're NOT Building (v1):**
- ~~[Cut item 1]~~ - Why: [reason]
- ~~[Cut item 2]~~ - Why: [reason]

**Ship Checklist:**

*Development*
- [ ] [Task 1] - Owner: [who]
- [ ] [Task 2] - Owner: [who]

*QA*
- [ ] [Task 1] - Owner: [who]

*Launch*
- [ ] [Task 1] - Owner: [who]

**Launch Criteria:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| [Metric 1] | [X] | [Y] | [How] |

**Definition of Done:**
- [ ] All must-have features complete
- [ ] Core user journey works end-to-end
- [ ] No P0 bugs
- [ ] Launch criteria measurement in place

## Important
- Be ruthless. If in doubt, cut it.
- Every feature you keep delays launch and learning.
- Perfect is the enemy of shipped.
- You can always add more in v1.1."""


def parse_executor_output(text: str) -> dict:
    """Parse Executor agent output into structured data."""
    return {
        "goal": extract_section(text, "Goal"),
        "core_value": extract_section(text, "Core Value Proposition"),
        "has_scope_table": "Scope Analysis" in text or "Classification" in text,
        "has_checklist": "Checklist" in text or "- [ ]" in text
    }


def create_executor_agent() -> BaseAgent:
    """Create and return the Executor agent."""
    config = AgentConfig(
        name="Executor",
        emoji="🚀",
        description="MVP scoping and shipping - cuts scope ruthlessly",
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
        tools=EXECUTOR_TOOLS,
        output_parser=parse_executor_output
    )
    return BaseAgent(config)
