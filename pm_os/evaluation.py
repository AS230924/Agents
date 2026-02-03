"""
PM OS Evaluation - Quality scoring and feedback tracking
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from enum import Enum


class Rating(Enum):
    """User feedback rating."""
    THUMBS_UP = "up"
    THUMBS_DOWN = "down"
    UNRATED = "unrated"


@dataclass
class QualityScore:
    """Quality score for an agent response."""
    completeness: int  # 1-5: Did it cover all aspects?
    actionability: int  # 1-5: Are outputs actionable?
    structure: int  # 1-5: Is it well-structured?
    relevance: int  # 1-5: Did it address the query?

    @property
    def total(self) -> float:
        return (self.completeness + self.actionability + self.structure + self.relevance) / 4

    def to_dict(self) -> dict:
        return {
            "completeness": self.completeness,
            "actionability": self.actionability,
            "structure": self.structure,
            "relevance": self.relevance,
            "total": round(self.total, 2)
        }


@dataclass
class Evaluation:
    """Evaluation record for a single interaction."""
    timestamp: str
    agent_name: str
    user_query: str
    response_length: int
    tools_used: list[str]
    user_rating: str = "unrated"
    user_feedback: str = ""
    auto_score: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Evaluation":
        return cls(**data)


# Agent-specific quality criteria
AGENT_CRITERIA = {
    "framer": {
        "name": "Framer",
        "criteria": [
            "Uses 5 Whys technique properly",
            "Identifies clear root cause",
            "Generates actionable problem statement",
            "Suggests concrete next steps"
        ],
        "key_sections": ["Surface Problem", "5 Whys", "Root Cause", "Problem Statement", "Next Steps"],
        "success_indicators": ["needs", "because", "root cause", "next step"]
    },
    "strategist": {
        "name": "Strategist",
        "criteria": [
            "Identifies all options clearly",
            "Uses consistent scoring criteria",
            "Provides clear recommendation",
            "Explains trade-offs"
        ],
        "key_sections": ["Options", "Scoring Matrix", "Recommendation", "Trade-offs", "Next Steps"],
        "success_indicators": ["recommendation", "score", "impact", "effort"]
    },
    "aligner": {
        "name": "Aligner",
        "criteria": [
            "Maps stakeholder motivations",
            "Identifies potential objections",
            "Provides talking points",
            "Includes clear ask"
        ],
        "key_sections": ["Stakeholder Map", "Motivations", "Objections", "Talking Points", "The Ask"],
        "success_indicators": ["motivation", "concern", "talking point", "ask"]
    },
    "executor": {
        "name": "Executor",
        "criteria": [
            "Defines clear MVP scope",
            "Ruthlessly cuts non-essentials",
            "Provides actionable checklist",
            "Sets launch criteria"
        ],
        "key_sections": ["MVP Definition", "Scope Analysis", "Ship Checklist", "Launch Criteria"],
        "success_indicators": ["must have", "cut", "mvp", "checklist"]
    },
    "narrator": {
        "name": "Narrator",
        "criteria": [
            "Clear TL;DR upfront",
            "WHAT section is factual",
            "WHY shows business impact",
            "ASK is specific and actionable"
        ],
        "key_sections": ["TL;DR", "WHAT", "WHY", "ASK"],
        "success_indicators": ["tl;dr", "what", "why", "ask", "decision needed"]
    },
    "doc_engine": {
        "name": "Doc Engine",
        "criteria": [
            "Includes all standard sections",
            "User stories are complete",
            "Requirements are testable",
            "Scope is clearly defined"
        ],
        "key_sections": ["Overview", "Problem Statement", "User Stories", "Requirements", "Scope", "Timeline"],
        "success_indicators": ["as a", "i want", "requirement", "in scope", "out of scope"]
    }
}


def auto_evaluate(agent_name: str, response: str) -> QualityScore:
    """
    Automatically evaluate response quality based on agent-specific criteria.
    """
    criteria = AGENT_CRITERIA.get(agent_name, {})
    response_lower = response.lower()

    # Check completeness - how many key sections are present
    key_sections = criteria.get("key_sections", [])
    sections_found = sum(1 for section in key_sections if section.lower() in response_lower)
    completeness = min(5, max(1, int((sections_found / max(len(key_sections), 1)) * 5)))

    # Check actionability - presence of action words and structure
    action_indicators = ["next step", "action", "recommend", "should", "checklist", "- [ ]"]
    action_count = sum(1 for ind in action_indicators if ind in response_lower)
    actionability = min(5, max(1, action_count + 1))

    # Check structure - markdown formatting
    structure_indicators = ["##", "**", "|", "- ", "1.", "```"]
    structure_count = sum(1 for ind in structure_indicators if ind in response)
    structure = min(5, max(1, int(structure_count / 2) + 1))

    # Check relevance - success indicators present
    success_indicators = criteria.get("success_indicators", [])
    indicators_found = sum(1 for ind in success_indicators if ind in response_lower)
    relevance = min(5, max(1, int((indicators_found / max(len(success_indicators), 1)) * 5) + 1))

    return QualityScore(
        completeness=completeness,
        actionability=actionability,
        structure=structure,
        relevance=relevance
    )


@dataclass
class EvaluationStore:
    """Store and analyze evaluations."""
    evaluations: list[Evaluation] = field(default_factory=list)

    def add_evaluation(
        self,
        agent_name: str,
        user_query: str,
        response: str,
        tools_used: list[str]
    ) -> Evaluation:
        """Add a new evaluation."""
        auto_score = auto_evaluate(agent_name, response)

        evaluation = Evaluation(
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            user_query=user_query[:200],
            response_length=len(response),
            tools_used=tools_used,
            auto_score=auto_score.to_dict()
        )
        self.evaluations.append(evaluation)
        return evaluation

    def rate_last(self, rating: str, feedback: str = "") -> bool:
        """Rate the most recent evaluation."""
        if not self.evaluations:
            return False
        self.evaluations[-1].user_rating = rating
        self.evaluations[-1].user_feedback = feedback
        return True

    def get_stats(self) -> dict:
        """Get aggregate statistics."""
        if not self.evaluations:
            return {
                "total_interactions": 0,
                "avg_score": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "by_agent": {}
            }

        total = len(self.evaluations)
        thumbs_up = sum(1 for e in self.evaluations if e.user_rating == "up")
        thumbs_down = sum(1 for e in self.evaluations if e.user_rating == "down")

        # Calculate average auto score
        scores = [e.auto_score["total"] for e in self.evaluations if e.auto_score]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Stats by agent
        by_agent = {}
        for e in self.evaluations:
            if e.agent_name not in by_agent:
                by_agent[e.agent_name] = {"count": 0, "thumbs_up": 0, "thumbs_down": 0, "scores": []}
            by_agent[e.agent_name]["count"] += 1
            if e.user_rating == "up":
                by_agent[e.agent_name]["thumbs_up"] += 1
            elif e.user_rating == "down":
                by_agent[e.agent_name]["thumbs_down"] += 1
            if e.auto_score:
                by_agent[e.agent_name]["scores"].append(e.auto_score["total"])

        # Calculate averages
        for agent in by_agent:
            scores = by_agent[agent]["scores"]
            by_agent[agent]["avg_score"] = round(sum(scores) / len(scores), 2) if scores else 0
            del by_agent[agent]["scores"]

        return {
            "total_interactions": total,
            "avg_score": round(avg_score, 2),
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": round(thumbs_up / (thumbs_up + thumbs_down) * 100, 1) if (thumbs_up + thumbs_down) > 0 else 0,
            "by_agent": by_agent
        }

    def get_stats_markdown(self) -> str:
        """Format stats as markdown for display."""
        stats = self.get_stats()

        if stats["total_interactions"] == 0:
            return "*No evaluations yet. Start chatting and rate responses to build your analytics!*"

        lines = [
            "## 📊 Evaluation Analytics\n",
            f"**Total Interactions:** {stats['total_interactions']}",
            f"**Average Quality Score:** {stats['avg_score']}/5.0",
            f"**User Satisfaction:** {stats['satisfaction_rate']}% ({stats['thumbs_up']} 👍 / {stats['thumbs_down']} 👎)\n",
            "### By Agent\n",
            "| Agent | Uses | Avg Score | 👍 | 👎 |",
            "|-------|------|-----------|----|----|"
        ]

        for agent, data in stats["by_agent"].items():
            emoji = AGENT_CRITERIA.get(agent, {}).get("name", agent)
            lines.append(f"| {emoji} | {data['count']} | {data['avg_score']} | {data['thumbs_up']} | {data['thumbs_down']} |")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "evaluations": [e.to_dict() for e in self.evaluations]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvaluationStore":
        store = cls()
        store.evaluations = [Evaluation.from_dict(e) for e in data.get("evaluations", [])]
        return store


# Global evaluation store
evaluation_store = EvaluationStore()


def get_evaluation_store() -> EvaluationStore:
    """Get the global evaluation store."""
    return evaluation_store


def reset_evaluation_store():
    """Reset the global evaluation store."""
    global evaluation_store
    evaluation_store = EvaluationStore()
