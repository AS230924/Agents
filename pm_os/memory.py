"""
PM OS Memory - Conversation history and decision logging
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class Decision:
    """Represents a key decision or recommendation made by an agent."""
    timestamp: str
    agent_name: str
    agent_emoji: str
    user_query: str
    decision_summary: str
    context: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Decision":
        return cls(**data)


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    timestamp: str
    user_message: str
    agent_name: str
    agent_response: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationTurn":
        return cls(**data)


@dataclass
class SessionMemory:
    """Memory for a single PM OS session."""
    session_id: str
    created_at: str
    conversation: list[ConversationTurn] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)

    def add_turn(self, user_message: str, agent_name: str, agent_response: str):
        """Add a conversation turn."""
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            agent_name=agent_name,
            agent_response=agent_response
        )
        self.conversation.append(turn)

    def add_decision(
        self,
        agent_name: str,
        agent_emoji: str,
        user_query: str,
        decision_summary: str,
        context: Optional[str] = None
    ):
        """Log a key decision."""
        decision = Decision(
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            agent_emoji=agent_emoji,
            user_query=user_query,
            decision_summary=decision_summary,
            context=context
        )
        self.decisions.append(decision)

    def get_decisions_markdown(self) -> str:
        """Format decisions as markdown for display."""
        if not self.decisions:
            return "*No decisions logged yet. Start chatting to build your decision log!*"

        lines = ["## 📋 Decision Log\n"]
        for i, d in enumerate(self.decisions, 1):
            time_str = datetime.fromisoformat(d.timestamp).strftime("%H:%M")
            lines.append(f"### {i}. {d.agent_emoji} {d.agent_name} ({time_str})")
            lines.append(f"**Query:** {d.user_query[:100]}{'...' if len(d.user_query) > 100 else ''}")
            lines.append(f"**Decision:** {d.decision_summary}")
            if d.context:
                lines.append(f"*Context: {d.context}*")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "conversation": [t.to_dict() for t in self.conversation],
            "decisions": [d.to_dict() for d in self.decisions]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMemory":
        memory = cls(
            session_id=data["session_id"],
            created_at=data["created_at"]
        )
        memory.conversation = [ConversationTurn.from_dict(t) for t in data.get("conversation", [])]
        memory.decisions = [Decision.from_dict(d) for d in data.get("decisions", [])]
        return memory

    def save(self, filepath: Optional[str] = None):
        """Save session to JSON file."""
        if filepath is None:
            filepath = f"pm_os_session_{self.session_id}.json"
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "SessionMemory":
        """Load session from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


def create_session() -> SessionMemory:
    """Create a new session with unique ID."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return SessionMemory(
        session_id=session_id,
        created_at=datetime.now().isoformat()
    )


def extract_decision_summary(agent_name: str, response: str) -> Optional[str]:
    """Extract the key decision/recommendation from an agent's response."""
    response_lower = response.lower()

    # Agent-specific extraction logic
    if agent_name == "strategist":
        # Look for recommendation section
        if "**recommendation:**" in response_lower:
            start = response_lower.find("**recommendation:**")
            end = response.find("\n\n", start)
            if end == -1:
                end = start + 200
            return response[start:end].replace("**Recommendation:**", "").strip()[:200]

    elif agent_name == "framer":
        # Look for problem statement
        if "**problem statement:**" in response_lower:
            start = response_lower.find("**problem statement:**")
            end = response.find("\n\n", start)
            if end == -1:
                end = start + 200
            return response[start:end].replace("**Problem Statement:**", "").strip()[:200]

    elif agent_name == "executor":
        # Look for MVP definition
        if "**mvp definition:**" in response_lower or "the mvp includes only:" in response_lower:
            start = response_lower.find("mvp")
            end = response.find("\n\n", start + 50)
            if end == -1:
                end = start + 200
            return "MVP defined: " + response[start:end].strip()[:150]

    elif agent_name == "aligner":
        # Look for alignment strategy or the ask
        if "**the ask:**" in response_lower:
            start = response_lower.find("**the ask:**")
            end = response.find("\n\n", start)
            if end == -1:
                end = start + 200
            return response[start:end].replace("**The Ask:**", "").strip()[:200]

    elif agent_name == "narrator":
        # Look for TL;DR
        if "**tl;dr:**" in response_lower:
            start = response_lower.find("**tl;dr:**")
            end = response.find("\n", start + 10)
            if end == -1:
                end = start + 200
            return response[start:end].replace("**TL;DR:**", "").strip()[:200]

    elif agent_name == "doc_engine":
        # Look for product name or primary goal
        if "**product name:**" in response_lower:
            start = response_lower.find("**product name:**")
            end = response.find("\n", start)
            return "Document created: " + response[start:end].replace("**Product Name:**", "").strip()[:100]

    # Fallback: first meaningful line after header
    lines = response.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("*") and len(line) > 20:
            return line[:200]

    return None
