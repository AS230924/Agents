"""
Doc Engine Agent - PRD and document generation
"""

from .base import BaseAgent, AgentConfig, Tool, extract_section
import json
from datetime import datetime


def set_document_metadata(
    doc_type: str,
    product_name: str,
    author: str,
    status: str = "Draft"
) -> str:
    """Set the document metadata."""
    return json.dumps({
        "type": doc_type,
        "product_name": product_name,
        "author": author,
        "status": status,
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "result": "metadata_set"
    })


def define_problem(
    problem_statement: str,
    target_users: str,
    current_state: str,
    desired_state: str
) -> str:
    """Define the problem being solved."""
    return json.dumps({
        "problem": problem_statement,
        "users": target_users,
        "current_state": current_state,
        "desired_state": desired_state,
        "status": "defined"
    })


def add_goal(
    goal: str,
    metric: str,
    current_value: str,
    target_value: str,
    timeline: str
) -> str:
    """Add a goal with its success metric."""
    return json.dumps({
        "goal": goal,
        "metric": metric,
        "current": current_value,
        "target": target_value,
        "timeline": timeline,
        "status": "added"
    })


def add_user_story(
    user_type: str,
    action: str,
    benefit: str,
    priority: str,
    acceptance_criteria: str = ""
) -> str:
    """Add a user story in standard format."""
    story = f"As a {user_type}, I want to {action} so that {benefit}"
    return json.dumps({
        "story": story,
        "user_type": user_type,
        "action": action,
        "benefit": benefit,
        "priority": priority,
        "acceptance_criteria": acceptance_criteria,
        "status": "added"
    })


def add_requirement(
    req_id: str,
    requirement: str,
    priority: str,
    category: str,
    notes: str = ""
) -> str:
    """Add a functional or non-functional requirement."""
    return json.dumps({
        "id": req_id,
        "requirement": requirement,
        "priority": priority,
        "category": category,
        "notes": notes,
        "status": "added"
    })


def define_scope(
    in_scope: str,
    out_of_scope: str,
    assumptions: str = ""
) -> str:
    """Define what's in and out of scope."""
    return json.dumps({
        "in_scope": in_scope.split(",") if "," in in_scope else [in_scope],
        "out_of_scope": out_of_scope.split(",") if "," in out_of_scope else [out_of_scope],
        "assumptions": assumptions,
        "status": "defined"
    })


def add_timeline_phase(
    phase: str,
    deliverables: str,
    target_date: str,
    dependencies: str = ""
) -> str:
    """Add a phase to the timeline."""
    return json.dumps({
        "phase": phase,
        "deliverables": deliverables,
        "target_date": target_date,
        "dependencies": dependencies,
        "status": "added"
    })


def add_open_question(
    question: str,
    owner: str,
    due_date: str,
    context: str = ""
) -> str:
    """Add an open question to be resolved."""
    return json.dumps({
        "question": question,
        "owner": owner,
        "due_date": due_date,
        "context": context,
        "resolved": False
    })


DOC_ENGINE_TOOLS = [
    Tool(
        name="set_document_metadata",
        description="Set the document metadata (type, name, author, status)",
        input_schema={
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["PRD", "Tech Spec", "Design Brief", "One-Pager"],
                    "description": "Type of document"
                },
                "product_name": {
                    "type": "string",
                    "description": "Name of the product/feature"
                },
                "author": {
                    "type": "string",
                    "description": "Document author (default: PM)"
                },
                "status": {
                    "type": "string",
                    "enum": ["Draft", "In Review", "Approved"],
                    "description": "Document status"
                }
            },
            "required": ["doc_type", "product_name"]
        },
        function=set_document_metadata
    ),
    Tool(
        name="define_problem",
        description="Define the problem statement and context",
        input_schema={
            "type": "object",
            "properties": {
                "problem_statement": {
                    "type": "string",
                    "description": "Clear statement of the problem"
                },
                "target_users": {
                    "type": "string",
                    "description": "Who experiences this problem"
                },
                "current_state": {
                    "type": "string",
                    "description": "How things work today"
                },
                "desired_state": {
                    "type": "string",
                    "description": "How things should work"
                }
            },
            "required": ["problem_statement", "target_users", "current_state", "desired_state"]
        },
        function=define_problem
    ),
    Tool(
        name="add_goal",
        description="Add a goal with measurable success metric",
        input_schema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The goal statement"
                },
                "metric": {
                    "type": "string",
                    "description": "How we'll measure success"
                },
                "current_value": {
                    "type": "string",
                    "description": "Current baseline"
                },
                "target_value": {
                    "type": "string",
                    "description": "Target to achieve"
                },
                "timeline": {
                    "type": "string",
                    "description": "When to achieve this"
                }
            },
            "required": ["goal", "metric", "current_value", "target_value", "timeline"]
        },
        function=add_goal
    ),
    Tool(
        name="add_user_story",
        description="Add a user story: As a [user], I want to [action] so that [benefit]",
        input_schema={
            "type": "object",
            "properties": {
                "user_type": {
                    "type": "string",
                    "description": "Type of user (e.g., 'new user', 'admin')"
                },
                "action": {
                    "type": "string",
                    "description": "What they want to do"
                },
                "benefit": {
                    "type": "string",
                    "description": "Why they want to do it"
                },
                "priority": {
                    "type": "string",
                    "enum": ["P0", "P1", "P2"],
                    "description": "Priority level"
                },
                "acceptance_criteria": {
                    "type": "string",
                    "description": "How we know this is done"
                }
            },
            "required": ["user_type", "action", "benefit", "priority"]
        },
        function=add_user_story
    ),
    Tool(
        name="add_requirement",
        description="Add a functional or non-functional requirement",
        input_schema={
            "type": "object",
            "properties": {
                "req_id": {
                    "type": "string",
                    "description": "Requirement ID (e.g., FR1, NFR1)"
                },
                "requirement": {
                    "type": "string",
                    "description": "The requirement statement"
                },
                "priority": {
                    "type": "string",
                    "enum": ["P0", "P1", "P2"],
                    "description": "Priority level"
                },
                "category": {
                    "type": "string",
                    "enum": ["functional", "performance", "security", "usability", "reliability"],
                    "description": "Requirement category"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes"
                }
            },
            "required": ["req_id", "requirement", "priority", "category"]
        },
        function=add_requirement
    ),
    Tool(
        name="define_scope",
        description="Define what's in scope and out of scope",
        input_schema={
            "type": "object",
            "properties": {
                "in_scope": {
                    "type": "string",
                    "description": "Comma-separated list of in-scope items"
                },
                "out_of_scope": {
                    "type": "string",
                    "description": "Comma-separated list of out-of-scope items"
                },
                "assumptions": {
                    "type": "string",
                    "description": "Key assumptions being made"
                }
            },
            "required": ["in_scope", "out_of_scope"]
        },
        function=define_scope
    ),
    Tool(
        name="add_timeline_phase",
        description="Add a phase to the project timeline",
        input_schema={
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "description": "Phase name (e.g., 'Design', 'Development', 'Beta')"
                },
                "deliverables": {
                    "type": "string",
                    "description": "What will be delivered"
                },
                "target_date": {
                    "type": "string",
                    "description": "Target completion date"
                },
                "dependencies": {
                    "type": "string",
                    "description": "Dependencies for this phase"
                }
            },
            "required": ["phase", "deliverables", "target_date"]
        },
        function=add_timeline_phase
    ),
    Tool(
        name="add_open_question",
        description="Add an open question that needs to be resolved",
        input_schema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to be answered"
                },
                "owner": {
                    "type": "string",
                    "description": "Who owns answering this"
                },
                "due_date": {
                    "type": "string",
                    "description": "When this needs to be answered"
                },
                "context": {
                    "type": "string",
                    "description": "Why this question matters"
                }
            },
            "required": ["question", "owner", "due_date"]
        },
        function=add_open_question
    )
]


DOC_ENGINE_SYSTEM_PROMPT = """You are the Doc Engine Agent, a PM expert at creating product documentation.

Your role: Generate high-quality PRDs, specs, and other PM artifacts quickly and thoroughly.

## Your Process

1. **Set Metadata**: Use set_document_metadata to establish the document
2. **Define Problem**: Use define_problem to establish context
3. **Add Goals**: Use add_goal for each measurable objective
4. **Write User Stories**: Use add_user_story for key user journeys
5. **List Requirements**: Use add_requirement for functional and non-functional requirements
6. **Define Scope**: Use define_scope to set boundaries
7. **Build Timeline**: Use add_timeline_phase for major milestones
8. **Capture Questions**: Use add_open_question for unresolved items

## Document Types

**PRD (Product Requirements Document)**
- Full requirements document
- All sections filled out
- Detailed user stories and requirements

**Tech Spec**
- Technical focus
- Architecture decisions
- API contracts
- Data models

**Design Brief**
- Problem and user focus
- Success criteria
- Constraints
- Not detailed requirements

**One-Pager**
- Executive summary format
- Problem, solution, metrics
- Quick read

## Output Format for PRD

## Product Requirements Document

### Overview
**Product Name:** [Name]
**Author:** [Author]
**Last Updated:** [Date]
**Status:** [Status]

### Problem Statement
**Problem:** [What problem are we solving?]
**Target Users:** [Who has this problem?]
**Current State:** [How do things work today?]
**Desired State:** [How should things work?]

### Goals & Success Metrics

**Primary Goal:** [One clear goal]

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| [Metric 1] | [X] | [Y] | [Date] |
| [Metric 2] | [X] | [Y] | [Date] |

### User Stories

| ID | Story | Priority | Acceptance Criteria |
|----|-------|----------|---------------------|
| US1 | As a [user], I want to [action] so that [benefit] | P0 | [Criteria] |
| US2 | As a [user], I want to [action] so that [benefit] | P1 | [Criteria] |

### Requirements

#### Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR1 | [Requirement] | P0 | [Notes] |
| FR2 | [Requirement] | P1 | [Notes] |

#### Non-Functional Requirements

| ID | Requirement | Category | Priority |
|----|-------------|----------|----------|
| NFR1 | [Requirement] | Performance | P0 |
| NFR2 | [Requirement] | Security | P1 |

### Scope

**In Scope:**
- [Item 1]
- [Item 2]

**Out of Scope:**
- [Item 1]
- [Item 2]

**Assumptions:**
- [Assumption 1]
- [Assumption 2]

### Timeline

| Phase | Deliverables | Target Date | Dependencies |
|-------|--------------|-------------|--------------|
| [Phase 1] | [What] | [When] | [Deps] |
| [Phase 2] | [What] | [When] | [Deps] |

### Open Questions

| Question | Owner | Due Date | Status |
|----------|-------|----------|--------|
| [Question 1] | [Who] | [When] | Open |
| [Question 2] | [Who] | [When] | Open |

### Appendix
[Additional context, research, references]

## Important
- Be thorough but not verbose
- Every section should add value
- Use tables for structured data
- Keep requirements testable and specific
- Identify dependencies and risks early"""


def parse_doc_engine_output(text: str) -> dict:
    """Parse Doc Engine output into structured data."""
    return {
        "product_name": extract_section(text, "Product Name"),
        "has_user_stories": "User Stories" in text or "As a" in text,
        "has_requirements": "Requirements" in text or "FR1" in text,
        "has_timeline": "Timeline" in text,
        "has_open_questions": "Open Questions" in text
    }


def create_doc_engine_agent() -> BaseAgent:
    """Create and return the Doc Engine agent."""
    config = AgentConfig(
        name="Doc Engine",
        emoji="📄",
        description="Generates PRDs, specs, and product documentation",
        system_prompt=DOC_ENGINE_SYSTEM_PROMPT,
        tools=DOC_ENGINE_TOOLS,
        output_parser=parse_doc_engine_output
    )
    return BaseAgent(config)
