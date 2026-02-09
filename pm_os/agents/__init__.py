"""
PM OS Agents - Enhanced agents with tool use and structured outputs
"""

from .base import BaseAgent, AgentConfig, Tool
from .framer import create_framer_agent
from .strategist import create_strategist_agent
from .aligner import create_aligner_agent
from .executor import create_executor_agent
from .narrator import create_narrator_agent
from .doc_engine import create_doc_engine_agent

# Create all agents
FRAMER = create_framer_agent()
STRATEGIST = create_strategist_agent()
ALIGNER = create_aligner_agent()
EXECUTOR = create_executor_agent()
NARRATOR = create_narrator_agent()
DOC_ENGINE = create_doc_engine_agent()

# Agent registry
AGENTS = {
    "framer": FRAMER,
    "strategist": STRATEGIST,
    "aligner": ALIGNER,
    "executor": EXECUTOR,
    "narrator": NARRATOR,
    "doc_engine": DOC_ENGINE,
}


def get_agent(name: str) -> BaseAgent:
    """Get an agent by name."""
    return AGENTS.get(name.lower())


def list_agents() -> list[dict]:
    """List all available agents with their info."""
    return [
        {
            "name": agent.name,
            "emoji": agent.emoji,
            "description": agent.description,
            "has_tools": len(agent.tools) > 0,
            "tool_count": len(agent.tools)
        }
        for agent in AGENTS.values()
    ]


__all__ = [
    "BaseAgent",
    "AgentConfig",
    "Tool",
    "AGENTS",
    "get_agent",
    "list_agents",
    "FRAMER",
    "STRATEGIST",
    "ALIGNER",
    "EXECUTOR",
    "NARRATOR",
    "DOC_ENGINE",
]
