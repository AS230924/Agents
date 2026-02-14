"""
Google Sheets export — creates user story spreadsheets.

Takes the Executor's user_stories JSON output and creates a Google Sheet with:
  - Header row with column names
  - One row per user story
  - Columns: ID, Story, Priority, Acceptance Criteria, Story Points,
             Sprint Fit, MVP Scope Item
  - Auto-sized columns and frozen header row
"""

import logging

from googleapiclient.discovery import build

from pm_os.export.google_auth import get_credentials

log = logging.getLogger(__name__)

_HEADERS = [
    "ID",
    "User Story",
    "Priority",
    "Acceptance Criteria",
    "Story Points",
    "Sprint Fit",
    "MVP Scope Item",
]


def _build_sheet_data(stories: list[dict]) -> list[list[str]]:
    """Convert user story dicts into rows for the spreadsheet."""
    rows = [_HEADERS]

    for story in stories:
        ac_list = story.get("acceptance_criteria", [])
        ac_text = "\n".join(ac_list) if ac_list else ""

        rows.append([
            story.get("id", ""),
            story.get("story", ""),
            story.get("priority", ""),
            ac_text,
            str(story.get("story_points", "")),
            story.get("sprint_fit", ""),
            story.get("mvp_scope_item", ""),
        ])

    return rows


def _build_format_requests(sheet_id: int, num_rows: int) -> list[dict]:
    """Build formatting requests for the sheet."""
    requests = []

    # Freeze header row
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    })

    # Bold header row
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": len(_HEADERS),
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"bold": True},
                    "backgroundColor": {
                        "red": 0.9,
                        "green": 0.93,
                        "blue": 0.98,
                    },
                }
            },
            "fields": "userEnteredFormat(textFormat,backgroundColor)",
        }
    })

    # Wrap text in Acceptance Criteria column (index 3)
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": num_rows,
                "startColumnIndex": 3,
                "endColumnIndex": 4,
            },
            "cell": {
                "userEnteredFormat": {"wrapStrategy": "WRAP"}
            },
            "fields": "userEnteredFormat.wrapStrategy",
        }
    })

    # Auto-resize columns
    requests.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": len(_HEADERS),
            }
        }
    })

    # Color-code priority column (index 2) using conditional formatting
    priority_colors = {
        "must-have": {"red": 0.96, "green": 0.80, "blue": 0.80},
        "should-have": {"red": 1.0, "green": 0.95, "blue": 0.80},
        "nice-to-have": {"red": 0.85, "green": 0.95, "blue": 0.85},
    }
    for priority, color in priority_colors.items():
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": num_rows,
                        "startColumnIndex": 2,
                        "endColumnIndex": 3,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": priority}],
                        },
                        "format": {"backgroundColor": color},
                    },
                },
                "index": 0,
            }
        })

    return requests


def export_stories_to_sheet(
    stories: list[dict],
    title: str = "User Stories",
    folder_id: str | None = None,
) -> dict:
    """
    Create a Google Sheet from a list of user story dicts.

    Args:
        stories: the Executor's user_stories list from agent JSON
        title: spreadsheet title
        folder_id: optional Google Drive folder ID to place the sheet in

    Returns:
        {"sheet_id": str, "sheet_url": str, "title": str}
    """
    creds = get_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    # 1. Create spreadsheet
    spreadsheet = sheets_service.spreadsheets().create(
        body={
            "properties": {"title": title},
            "sheets": [{"properties": {"title": "User Stories"}}],
        }
    ).execute()

    spreadsheet_id = spreadsheet["spreadsheetId"]
    sheet_id = spreadsheet["sheets"][0]["properties"]["sheetId"]
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    log.info("Created Google Sheet: %s (%s)", title, sheet_url)

    # 2. Write data
    rows = _build_sheet_data(stories)
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="User Stories!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

    # 3. Apply formatting
    format_requests = _build_format_requests(sheet_id, len(rows))
    if format_requests:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": format_requests},
        ).execute()

    # 4. Move to folder if specified
    if folder_id:
        drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            fields="id, parents",
        ).execute()
        log.info("Moved sheet to folder: %s", folder_id)

    return {
        "sheet_id": spreadsheet_id,
        "sheet_url": sheet_url,
        "title": title,
    }
