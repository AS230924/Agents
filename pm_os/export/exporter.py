"""
Unified document exporter — routes Executor output to Google Docs/Sheets.

Takes the Executor agent's structured JSON output and creates the
appropriate Google Workspace documents:
  - PRD output_type → Google Doc
  - user_stories output_type → Google Sheet
  - combined output_type → both Google Doc + Google Sheet

Usage:
    from pm_os.export.exporter import export_agent_output
    result = export_agent_output(executor_output, folder_id="optional_folder_id")
"""

import logging
import os

log = logging.getLogger(__name__)


def export_agent_output(
    agent_output: dict,
    folder_id: str | None = None,
) -> dict:
    """
    Export Executor agent output to Google Docs/Sheets.

    Args:
        agent_output: the Executor's primary_output dict. Must contain
                      "output_type" and the corresponding data fields.
        folder_id: optional Google Drive folder ID. Falls back to
                   GOOGLE_DRIVE_FOLDER_ID env var.

    Returns:
        {
            "exported": True/False,
            "documents": [
                {"type": "prd", "doc_id": "...", "doc_url": "...", "title": "..."},
                {"type": "user_stories", "sheet_id": "...", "sheet_url": "...", "title": "..."},
            ],
            "error": "..." (only if exported=False)
        }
    """
    if agent_output.get("status") != "complete":
        return {
            "exported": False,
            "documents": [],
            "error": "Agent output status is not 'complete' — nothing to export",
        }

    output_type = agent_output.get("output_type", "execution_plan")
    folder = folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    documents = []

    try:
        if output_type in ("prd", "combined"):
            prd_data = agent_output.get("prd")
            if prd_data:
                doc_result = _export_prd(prd_data, folder)
                documents.append({"type": "prd", **doc_result})

        if output_type in ("user_stories", "combined"):
            stories_data = agent_output.get("user_stories")
            if stories_data:
                sheet_title = _derive_stories_title(agent_output)
                sheet_result = _export_stories(stories_data, sheet_title, folder)
                documents.append({"type": "user_stories", **sheet_result})

    except FileNotFoundError as e:
        log.error("Google credentials not configured: %s", e)
        return {
            "exported": False,
            "documents": [],
            "error": f"Google credentials not configured: {e}",
        }
    except Exception as e:
        log.error("Export failed: %s", e)
        return {
            "exported": False,
            "documents": documents,
            "error": str(e),
        }

    if not documents:
        return {
            "exported": False,
            "documents": [],
            "error": f"No exportable content found for output_type '{output_type}'",
        }

    return {"exported": True, "documents": documents}


def _export_prd(prd_data: dict, folder_id: str | None) -> dict:
    """Export PRD to Google Docs."""
    from pm_os.export.docs_export import export_prd_to_doc

    return export_prd_to_doc(prd_data, folder_id=folder_id)


def _export_stories(
    stories: list[dict], title: str, folder_id: str | None
) -> dict:
    """Export user stories to Google Sheets."""
    from pm_os.export.sheets_export import export_stories_to_sheet

    return export_stories_to_sheet(stories, title=title, folder_id=folder_id)


def _derive_stories_title(agent_output: dict) -> str:
    """Derive a sheet title from the agent output context."""
    prd = agent_output.get("prd", {})
    if prd and prd.get("title"):
        return f"User Stories — {prd['title']}"

    decision = agent_output.get("decision_context", "")
    if decision:
        return f"User Stories — {decision[:60]}"

    return "User Stories"
