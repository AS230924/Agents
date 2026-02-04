"""
PM OS Notion Integration - Export agent outputs to Notion databases
"""

import json
import urllib.request
import urllib.parse
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


# Global configuration
_notion_token: Optional[str] = None

# Agent-specific database IDs
_db_ids: dict = {
    "decision": None,
    "framer": None,
    "strategist": None,
    "aligner": None,
    "executor": None,
    "narrator": None,
    "doc_engine": None,
}

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"


def set_notion_config(
    token: str,
    decision_db_id: str = None,
    framer_db_id: str = None,
    strategist_db_id: str = None,
    aligner_db_id: str = None,
    executor_db_id: str = None,
    narrator_db_id: str = None,
    doc_engine_db_id: str = None
):
    """Set Notion API configuration."""
    global _notion_token, _db_ids
    _notion_token = token

    if decision_db_id:
        _db_ids["decision"] = decision_db_id
    if framer_db_id:
        _db_ids["framer"] = framer_db_id
    if strategist_db_id:
        _db_ids["strategist"] = strategist_db_id
    if aligner_db_id:
        _db_ids["aligner"] = aligner_db_id
    if executor_db_id:
        _db_ids["executor"] = executor_db_id
    if narrator_db_id:
        _db_ids["narrator"] = narrator_db_id
    if doc_engine_db_id:
        _db_ids["doc_engine"] = doc_engine_db_id


def set_agent_db_id(agent_name: str, db_id: str):
    """Set database ID for a specific agent."""
    global _db_ids
    key = agent_name.lower().replace(" ", "_")
    if key in _db_ids:
        _db_ids[key] = db_id


def get_notion_token() -> Optional[str]:
    """Get Notion token."""
    return _notion_token


def get_db_id(agent_name: str) -> Optional[str]:
    """Get database ID for an agent."""
    key = agent_name.lower().replace(" ", "_")
    return _db_ids.get(key)


def get_decision_db_id() -> Optional[str]:
    """Get Decision database ID (backwards compatibility)."""
    return _db_ids.get("decision")


def _make_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make a request to Notion API."""
    token = get_notion_token()
    if not token:
        raise ValueError("Notion token not configured")

    url = f"{NOTION_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION
    }

    request = urllib.request.Request(url, headers=headers, method=method)

    if data:
        request.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"Notion API error ({e.code}): {error_body}")


def _create_text_property(content: str, max_length: int = 2000) -> dict:
    """Create a rich_text property."""
    return {
        "rich_text": [
            {"text": {"content": content[:max_length] if content else ""}}
        ]
    }


def _create_title_property(content: str) -> dict:
    """Create a title property."""
    return {
        "title": [
            {"text": {"content": content[:100] if content else ""}}
        ]
    }


def _create_date_property(date: datetime = None) -> dict:
    """Create a date property."""
    if date is None:
        date = datetime.now()
    return {
        "date": {"start": date.strftime("%Y-%m-%d")}
    }


def _create_status_property(status: str = "Done") -> dict:
    """Create a status property."""
    return {
        "status": {"name": status}
    }


# ============================================================
# FRAMER EXPORT
# Database columns: Problem ID, Date, Surface Problem, Root Cause,
#                   Problem Statement, Next Steps, Status
# ============================================================

def export_framer(
    problem_id: str,
    surface_problem: str,
    root_cause: str,
    problem_statement: str,
    next_steps: str,
    status: str = "Done",
    date: datetime = None
) -> dict:
    """Export Framer agent output to Notion."""
    db_id = get_db_id("framer")
    if not db_id:
        raise ValueError("Framer database ID not configured")

    properties = {
        "Problem ID": _create_title_property(problem_id),
        "Date": _create_date_property(date),
        "Surface Problem": _create_text_property(surface_problem),
        "Root Cause": _create_text_property(root_cause),
        "Problem Statement": _create_text_property(problem_statement),
        "Next Steps": _create_text_property(next_steps),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


# ============================================================
# STRATEGIST EXPORT
# Database columns: Decision ID, Date, Options, Scores,
#                   Recommendation, Tradeoffs, Status
# ============================================================

def export_strategist(
    decision_id: str,
    options: str,
    scores: str,
    recommendation: str,
    tradeoffs: str,
    status: str = "Done",
    date: datetime = None
) -> dict:
    """Export Strategist agent output to Notion."""
    db_id = get_db_id("strategist")
    if not db_id:
        raise ValueError("Strategist database ID not configured")

    properties = {
        "Decision ID": _create_title_property(decision_id),
        "Date": _create_date_property(date),
        "Options": _create_text_property(options),
        "Scores": _create_text_property(scores),
        "Recommendation": _create_text_property(recommendation),
        "Tradeoffs": _create_text_property(tradeoffs),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


# ============================================================
# ALIGNER EXPORT
# Database columns: Meeting ID, Date, Stakeholders, The Ask,
#                   Talking Points, Objection Responses, Status
# ============================================================

def export_aligner(
    meeting_id: str,
    stakeholders: str,
    the_ask: str,
    talking_points: str,
    objection_responses: str,
    status: str = "Done",
    date: datetime = None
) -> dict:
    """Export Aligner agent output to Notion."""
    db_id = get_db_id("aligner")
    if not db_id:
        raise ValueError("Aligner database ID not configured")

    properties = {
        "Meeting ID": _create_title_property(meeting_id),
        "Date": _create_date_property(date),
        "Stakeholders": _create_text_property(stakeholders),
        "The Ask": _create_text_property(the_ask),
        "Talking Points": _create_text_property(talking_points),
        "Objection Responses": _create_text_property(objection_responses),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


# ============================================================
# EXECUTOR EXPORT
# Database columns: MVP ID, Date, Features, MVP Scope,
#                   Cut List, Launch Criteria, Status
# ============================================================

def export_executor(
    mvp_id: str,
    features: str,
    mvp_scope: str,
    cut_list: str,
    launch_criteria: str,
    status: str = "Done",
    date: datetime = None
) -> dict:
    """Export Executor agent output to Notion."""
    db_id = get_db_id("executor")
    if not db_id:
        raise ValueError("Executor database ID not configured")

    properties = {
        "MVP ID": _create_title_property(mvp_id),
        "Date": _create_date_property(date),
        "Features": _create_text_property(features),
        "MVP Scope": _create_text_property(mvp_scope),
        "Cut List": _create_text_property(cut_list),
        "Launch Criteria": _create_text_property(launch_criteria),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


# ============================================================
# NARRATOR EXPORT
# Database columns: Summary ID, Date, TL;DR, What, Why,
#                   The Ask, Status
# ============================================================

def export_narrator(
    summary_id: str,
    tldr: str,
    what: str,
    why: str,
    the_ask: str,
    status: str = "Done",
    date: datetime = None
) -> dict:
    """Export Narrator agent output to Notion."""
    db_id = get_db_id("narrator")
    if not db_id:
        raise ValueError("Narrator database ID not configured")

    properties = {
        "Summary ID": _create_title_property(summary_id),
        "Date": _create_date_property(date),
        "TL;DR": _create_text_property(tldr),
        "What": _create_text_property(what),
        "Why": _create_text_property(why),
        "The Ask": _create_text_property(the_ask),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


# ============================================================
# DOC ENGINE EXPORT
# Database columns: PRD ID, Date, Problem, Goals, User Stories,
#                   Requirements, Timeline, Status
# ============================================================

def export_doc_engine(
    prd_id: str,
    problem: str,
    goals: str,
    user_stories: str,
    requirements: str,
    timeline: str,
    status: str = "Done",
    date: datetime = None
) -> dict:
    """Export Doc Engine agent output to Notion."""
    db_id = get_db_id("doc_engine")
    if not db_id:
        raise ValueError("Doc Engine database ID not configured")

    properties = {
        "PRD ID": _create_title_property(prd_id),
        "Date": _create_date_property(date),
        "Problem": _create_text_property(problem),
        "Goals": _create_text_property(goals),
        "User Stories": _create_text_property(user_stories),
        "Requirements": _create_text_property(requirements),
        "Timeline": _create_text_property(timeline),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


# ============================================================
# GENERIC DECISION EXPORT (backwards compatibility)
# ============================================================

def create_decision_page(
    decision_id: str,
    summary: str,
    rationale: str,
    revisit_if: str = "",
    status: str = "In progress",
    date: datetime = None
) -> dict:
    """Create a new decision entry in the Notion database."""
    db_id = get_decision_db_id()
    if not db_id:
        raise ValueError("Decision database ID not configured")

    if date is None:
        date = datetime.now()

    properties = {
        "Decision ID": _create_title_property(decision_id),
        "Date": _create_date_property(date),
        "Summary": _create_text_property(summary),
        "Rationale": _create_text_property(rationale),
        "Revisit If": _create_text_property(revisit_if),
        "Status": _create_status_property(status),
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    return _make_request("/pages", method="POST", data=data)


def export_decision(decision: dict) -> dict:
    """Export a Decision object to Notion."""
    agent = decision.get("agent_name", "Unknown")
    emoji = decision.get("agent_emoji", "📝")
    timestamp = decision.get("timestamp", datetime.now().isoformat())
    query = decision.get("user_query", "")
    summary = decision.get("decision_summary", "")

    try:
        if isinstance(timestamp, str):
            date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            date = timestamp
    except:
        date = datetime.now()

    decision_id = f"{emoji} {agent}: {query[:50]}"

    return create_decision_page(
        decision_id=decision_id,
        summary=summary,
        rationale=f"Generated by {agent} agent in response to: {query}",
        revisit_if="Review if context changes significantly",
        status="Done",
        date=date
    )


def export_all_decisions(decisions: list) -> list:
    """Export multiple decisions to Notion."""
    results = []
    for decision in decisions:
        try:
            result = export_decision(decision)
            results.append({"success": True, "result": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    return results


# ============================================================
# SMART EXPORT - Routes to correct agent database
# ============================================================

def export_agent_output(agent_name: str, query: str, response: str, parsed_data: dict = None) -> dict:
    """
    Smart export that routes to the correct agent database.

    Args:
        agent_name: Name of the agent (framer, strategist, etc.)
        query: User's original query
        response: Full agent response text
        parsed_data: Optional pre-parsed data from agent output parser

    Returns:
        Response from Notion API
    """
    agent_key = agent_name.lower().replace(" ", "_")
    date = datetime.now()

    if agent_key == "framer":
        return export_framer(
            problem_id=f"🔍 {query[:50]}",
            surface_problem=parsed_data.get("surface_problem", query) if parsed_data else query,
            root_cause=parsed_data.get("root_cause", "") if parsed_data else _extract_section(response, "Root Cause"),
            problem_statement=parsed_data.get("problem_statement", "") if parsed_data else _extract_section(response, "Problem Statement"),
            next_steps=_extract_section(response, "Next Steps") or _extract_section(response, "Recommended"),
            date=date
        )

    elif agent_key == "strategist":
        return export_strategist(
            decision_id=f"📊 {query[:50]}",
            options=_extract_section(response, "Options") or _extract_section(response, "Option"),
            scores=_extract_section(response, "Score") or _extract_section(response, "Scoring"),
            recommendation=_extract_section(response, "Recommendation"),
            tradeoffs=_extract_section(response, "Trade") or _extract_section(response, "Tradeoff"),
            date=date
        )

    elif agent_key == "aligner":
        return export_aligner(
            meeting_id=f"🤝 {query[:50]}",
            stakeholders=_extract_section(response, "Stakeholder"),
            the_ask=_extract_section(response, "The Ask") or _extract_section(response, "Ask"),
            talking_points=_extract_section(response, "Talking Point"),
            objection_responses=_extract_section(response, "Objection"),
            date=date
        )

    elif agent_key == "executor":
        return export_executor(
            mvp_id=f"🚀 {query[:50]}",
            features=_extract_section(response, "Feature"),
            mvp_scope=_extract_section(response, "MVP") or _extract_section(response, "Scope"),
            cut_list=_extract_section(response, "Cut") or _extract_section(response, "Deferred"),
            launch_criteria=_extract_section(response, "Launch") or _extract_section(response, "Criteria"),
            date=date
        )

    elif agent_key == "narrator":
        return export_narrator(
            summary_id=f"📝 {query[:50]}",
            tldr=_extract_section(response, "TL;DR") or _extract_section(response, "TLDR"),
            what=_extract_section(response, "What"),
            why=_extract_section(response, "Why"),
            the_ask=_extract_section(response, "Ask"),
            date=date
        )

    elif agent_key == "doc_engine":
        return export_doc_engine(
            prd_id=f"📄 {query[:50]}",
            problem=_extract_section(response, "Problem"),
            goals=_extract_section(response, "Goal"),
            user_stories=_extract_section(response, "User Stor") or _extract_section(response, "Stories"),
            requirements=_extract_section(response, "Requirement"),
            timeline=_extract_section(response, "Timeline") or _extract_section(response, "Phase"),
            date=date
        )

    else:
        raise ValueError(f"Unknown agent: {agent_name}")


def _extract_section(text: str, section_name: str) -> str:
    """Extract a section from markdown text."""
    text_lower = text.lower()
    section_lower = section_name.lower()

    # Try to find section header
    patterns = [
        f"**{section_lower}",
        f"## {section_lower}",
        f"### {section_lower}",
        f"# {section_lower}",
        f"{section_lower}:",
    ]

    start_idx = -1
    for pattern in patterns:
        idx = text_lower.find(pattern)
        if idx != -1:
            start_idx = idx
            break

    if start_idx == -1:
        return ""

    # Find end of section (next header or end of text)
    end_idx = len(text)
    for marker in ["\n## ", "\n### ", "\n**", "\n---"]:
        idx = text.find(marker, start_idx + len(section_name) + 5)
        if idx != -1 and idx < end_idx:
            end_idx = idx

    section = text[start_idx:end_idx].strip()

    # Clean up the section
    lines = section.split("\n")
    if len(lines) > 1:
        section = "\n".join(lines[1:]).strip()  # Remove header line

    return section[:2000]  # Notion limit


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def test_connection() -> bool:
    """Test if Notion connection is working."""
    try:
        token = get_notion_token()
        if not token:
            return False
        _make_request("/users/me")
        return True
    except:
        return False


def get_database_info(db_name: str = "decision") -> dict:
    """Get info about a configured database."""
    db_id = get_db_id(db_name)
    if not db_id:
        raise ValueError(f"{db_name} database ID not configured")
    return _make_request(f"/databases/{db_id}")


def get_configured_databases() -> dict:
    """Get list of configured database IDs."""
    return {k: v for k, v in _db_ids.items() if v is not None}
