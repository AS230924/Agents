"""
PM OS Google Sheets Export - Export agent outputs to CSV for Google Sheets
"""

import csv
import io
from datetime import datetime
from typing import Optional


# Sheet ID storage
_sheet_id: Optional[str] = None


def set_sheet_id(sheet_id: str):
    """Set the Google Sheet ID."""
    global _sheet_id
    _sheet_id = sheet_id


def get_sheet_id() -> Optional[str]:
    """Get the Google Sheet ID."""
    return _sheet_id


def get_sheet_url() -> Optional[str]:
    """Get the full Google Sheet URL."""
    if _sheet_id:
        return f"https://docs.google.com/spreadsheets/d/{_sheet_id}/edit"
    return None


# ============================================================
# CSV GENERATORS FOR EACH AGENT
# ============================================================

def generate_decisions_csv(decisions: list) -> str:
    """
    Generate CSV for the Decisions tab.
    Columns: Date, Agent, Query, Decision, Score
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Date", "Agent", "Query", "Decision", "Score"])

    for d in decisions:
        writer.writerow([
            d.get("timestamp", datetime.now().isoformat())[:10],
            f"{d.get('agent_emoji', '')} {d.get('agent_name', 'Unknown')}",
            d.get("user_query", "")[:200],
            d.get("decision_summary", "")[:500],
            d.get("score", "")
        ])

    return output.getvalue()


def generate_framer_csv(outputs: list) -> str:
    """
    Generate CSV for the Framer tab.
    Columns: Date, Query, Surface Problem, Root Cause, Problem Statement, Next Steps
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Query", "Surface Problem", "Root Cause", "Problem Statement", "Next Steps"])

    for o in outputs:
        writer.writerow([
            o.get("date", datetime.now().strftime("%Y-%m-%d")),
            o.get("query", "")[:200],
            o.get("surface_problem", "")[:500],
            o.get("root_cause", "")[:500],
            o.get("problem_statement", "")[:500],
            o.get("next_steps", "")[:500]
        ])

    return output.getvalue()


def generate_strategist_csv(outputs: list) -> str:
    """
    Generate CSV for the Strategist tab.
    Columns: Date, Query, Options, Scores, Recommendation, Tradeoffs
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Query", "Options", "Scores", "Recommendation", "Tradeoffs"])

    for o in outputs:
        writer.writerow([
            o.get("date", datetime.now().strftime("%Y-%m-%d")),
            o.get("query", "")[:200],
            o.get("options", "")[:500],
            o.get("scores", "")[:500],
            o.get("recommendation", "")[:500],
            o.get("tradeoffs", "")[:500]
        ])

    return output.getvalue()


def generate_aligner_csv(outputs: list) -> str:
    """
    Generate CSV for the Aligner tab.
    Columns: Date, Query, Stakeholders, The Ask, Talking Points, Objections
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Query", "Stakeholders", "The Ask", "Talking Points", "Objections"])

    for o in outputs:
        writer.writerow([
            o.get("date", datetime.now().strftime("%Y-%m-%d")),
            o.get("query", "")[:200],
            o.get("stakeholders", "")[:500],
            o.get("the_ask", "")[:500],
            o.get("talking_points", "")[:500],
            o.get("objections", "")[:500]
        ])

    return output.getvalue()


def generate_executor_csv(outputs: list) -> str:
    """
    Generate CSV for the Executor tab.
    Columns: Date, Query, Features, MVP Scope, Cut List, Launch Criteria
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Query", "Features", "MVP Scope", "Cut List", "Launch Criteria"])

    for o in outputs:
        writer.writerow([
            o.get("date", datetime.now().strftime("%Y-%m-%d")),
            o.get("query", "")[:200],
            o.get("features", "")[:500],
            o.get("mvp_scope", "")[:500],
            o.get("cut_list", "")[:500],
            o.get("launch_criteria", "")[:500]
        ])

    return output.getvalue()


def generate_narrator_csv(outputs: list) -> str:
    """
    Generate CSV for the Narrator tab.
    Columns: Date, Query, TL;DR, What, Why, The Ask
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Query", "TL;DR", "What", "Why", "The Ask"])

    for o in outputs:
        writer.writerow([
            o.get("date", datetime.now().strftime("%Y-%m-%d")),
            o.get("query", "")[:200],
            o.get("tldr", "")[:500],
            o.get("what", "")[:500],
            o.get("why", "")[:500],
            o.get("the_ask", "")[:500]
        ])

    return output.getvalue()


def generate_doc_engine_csv(outputs: list) -> str:
    """
    Generate CSV for the Doc Engine tab.
    Columns: Date, Query, Problem, Goals, User Stories, Requirements, Timeline
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Query", "Problem", "Goals", "User Stories", "Requirements", "Timeline"])

    for o in outputs:
        writer.writerow([
            o.get("date", datetime.now().strftime("%Y-%m-%d")),
            o.get("query", "")[:200],
            o.get("problem", "")[:500],
            o.get("goals", "")[:500],
            o.get("user_stories", "")[:500],
            o.get("requirements", "")[:500],
            o.get("timeline", "")[:500]
        ])

    return output.getvalue()


# ============================================================
# RESPONSE PARSER - Extract structured data from agent responses
# ============================================================

def extract_section(text: str, section_name: str) -> str:
    """Extract a section from markdown text."""
    if not text:
        return ""

    text_lower = text.lower()
    section_lower = section_name.lower()

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

    end_idx = len(text)
    for marker in ["\n## ", "\n### ", "\n**", "\n---"]:
        idx = text.find(marker, start_idx + len(section_name) + 5)
        if idx != -1 and idx < end_idx:
            end_idx = idx

    section = text[start_idx:end_idx].strip()

    lines = section.split("\n")
    if len(lines) > 1:
        section = "\n".join(lines[1:]).strip()

    return section[:500]


def parse_agent_response(agent_name: str, query: str, response: str) -> dict:
    """
    Parse an agent response into structured data for CSV export.
    """
    agent_key = agent_name.lower().replace(" ", "_")
    date = datetime.now().strftime("%Y-%m-%d")

    base_data = {
        "date": date,
        "query": query,
        "agent_name": agent_name
    }

    if agent_key == "framer":
        return {
            **base_data,
            "surface_problem": extract_section(response, "Surface Problem") or query,
            "root_cause": extract_section(response, "Root Cause"),
            "problem_statement": extract_section(response, "Problem Statement"),
            "next_steps": extract_section(response, "Next Steps") or extract_section(response, "Recommended")
        }

    elif agent_key == "strategist":
        return {
            **base_data,
            "options": extract_section(response, "Options") or extract_section(response, "Option"),
            "scores": extract_section(response, "Score") or extract_section(response, "Scoring"),
            "recommendation": extract_section(response, "Recommendation"),
            "tradeoffs": extract_section(response, "Trade") or extract_section(response, "Tradeoff")
        }

    elif agent_key == "aligner":
        return {
            **base_data,
            "stakeholders": extract_section(response, "Stakeholder"),
            "the_ask": extract_section(response, "The Ask") or extract_section(response, "Ask"),
            "talking_points": extract_section(response, "Talking Point"),
            "objections": extract_section(response, "Objection")
        }

    elif agent_key == "executor":
        return {
            **base_data,
            "features": extract_section(response, "Feature"),
            "mvp_scope": extract_section(response, "MVP") or extract_section(response, "Scope"),
            "cut_list": extract_section(response, "Cut") or extract_section(response, "Deferred"),
            "launch_criteria": extract_section(response, "Launch") or extract_section(response, "Criteria")
        }

    elif agent_key == "narrator":
        return {
            **base_data,
            "tldr": extract_section(response, "TL;DR") or extract_section(response, "TLDR"),
            "what": extract_section(response, "What"),
            "why": extract_section(response, "Why"),
            "the_ask": extract_section(response, "Ask")
        }

    elif agent_key == "doc_engine":
        return {
            **base_data,
            "problem": extract_section(response, "Problem"),
            "goals": extract_section(response, "Goal"),
            "user_stories": extract_section(response, "User Stor") or extract_section(response, "Stories"),
            "requirements": extract_section(response, "Requirement"),
            "timeline": extract_section(response, "Timeline") or extract_section(response, "Phase")
        }

    return base_data


# ============================================================
# COMBINED EXPORT
# ============================================================

def generate_all_outputs_csv(conversation_turns: list) -> str:
    """
    Generate a single CSV with all outputs from all agents.
    Columns: Date, Agent, Query, Response Summary
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Agent", "Query", "Response Summary"])

    for turn in conversation_turns:
        # Truncate response to first 500 chars for summary
        response = turn.get("agent_response", "")
        summary = response[:500] + "..." if len(response) > 500 else response
        # Clean newlines for CSV
        summary = summary.replace("\n", " ").replace("\r", "")

        writer.writerow([
            turn.get("timestamp", "")[:10],
            turn.get("agent_name", "Unknown"),
            turn.get("user_message", "")[:200],
            summary
        ])

    return output.getvalue()
