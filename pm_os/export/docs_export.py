"""
Google Docs export — creates formatted PRD documents.

Takes the Executor's PRD JSON output and creates a styled Google Doc with:
  - Title + metadata header
  - Problem statement, objectives, success metrics
  - Functional & non-functional requirements tables
  - Scope (in/out), assumptions, constraints, dependencies
  - Timeline and release strategy
"""

import logging

from googleapiclient.discovery import build

from pm_os.export.google_auth import get_credentials

log = logging.getLogger(__name__)


def _build_prd_requests(prd: dict) -> list[dict]:
    """
    Convert a PRD dict into a list of Google Docs API batchUpdate requests.

    Inserts content in reverse order (bottom-up) so character indices
    don't shift as we insert. Each section is inserted at index 1 (start of body).
    """
    requests = []
    # We build sections bottom-up, so the final document reads top-down.
    sections = []

    # --- Release Strategy ---
    if prd.get("release_strategy"):
        sections.append(("Release Strategy", prd["release_strategy"]))

    # --- Timeline ---
    if prd.get("timeline"):
        sections.append(("Timeline", prd["timeline"]))

    # --- Dependencies ---
    if prd.get("dependencies"):
        body = "\n".join(f"  - {d}" for d in prd["dependencies"])
        sections.append(("Dependencies", body))

    # --- Constraints ---
    if prd.get("constraints"):
        body = "\n".join(f"  - {c}" for c in prd["constraints"])
        sections.append(("Constraints", body))

    # --- Assumptions ---
    if prd.get("assumptions"):
        body = "\n".join(f"  - {a}" for a in prd["assumptions"])
        sections.append(("Assumptions", body))

    # --- Scope ---
    scope = prd.get("scope", {})
    if scope:
        lines = []
        if scope.get("in_scope"):
            lines.append("In Scope:")
            lines.extend(f"  - {item}" for item in scope["in_scope"])
        if scope.get("out_of_scope"):
            lines.append("Out of Scope:")
            lines.extend(f"  - {item}" for item in scope["out_of_scope"])
        sections.append(("Scope", "\n".join(lines)))

    # --- Non-Functional Requirements ---
    nfrs = prd.get("non_functional_requirements", [])
    if nfrs:
        lines = []
        for nfr in nfrs:
            nfr_id = nfr.get("id", "NFR-?")
            cat = nfr.get("category", "general")
            req = nfr.get("requirement", "")
            lines.append(f"  [{nfr_id}] ({cat}) {req}")
        sections.append(("Non-Functional Requirements", "\n".join(lines)))

    # --- Functional Requirements ---
    frs = prd.get("functional_requirements", [])
    if frs:
        lines = []
        for fr in frs:
            fr_id = fr.get("id", "FR-?")
            priority = fr.get("priority", "")
            req = fr.get("requirement", "")
            lines.append(f"  [{fr_id}] ({priority}) {req}")
        sections.append(("Functional Requirements", "\n".join(lines)))

    # --- Target Users ---
    if prd.get("target_users"):
        body = "\n".join(f"  - {u}" for u in prd["target_users"])
        sections.append(("Target Users", body))

    # --- Success Metrics ---
    metrics = prd.get("success_metrics", {})
    if metrics:
        lines = []
        if metrics.get("primary"):
            lines.append(f"  Primary: {metrics['primary']}")
        if metrics.get("guardrail"):
            lines.append(f"  Guardrail: {metrics['guardrail']}")
        sections.append(("Success Metrics", "\n".join(lines)))

    # --- Objective ---
    if prd.get("objective"):
        sections.append(("Objective", prd["objective"]))

    # --- Problem Statement ---
    if prd.get("problem_statement"):
        sections.append(("Problem Statement", prd["problem_statement"]))

    # Now build the insert requests bottom-up (reverse order so indices are stable)
    # We insert at index 1 each time, pushing previous content down
    for heading, body in sections:
        # Insert body text first (it will be pushed down by heading)
        requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": f"{body}\n\n",
            }
        })
        # Insert heading
        requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": f"{heading}\n",
            }
        })

    return requests


def _build_heading_style_requests(doc_content: str) -> list[dict]:
    """
    After all text is inserted, apply HEADING_2 style to section headings.

    Scans the document text for known section headings and applies paragraph
    styling to those ranges.
    """
    requests = []
    headings = [
        "Problem Statement",
        "Objective",
        "Success Metrics",
        "Target Users",
        "Functional Requirements",
        "Non-Functional Requirements",
        "Scope",
        "Assumptions",
        "Constraints",
        "Dependencies",
        "Timeline",
        "Release Strategy",
    ]

    for heading in headings:
        start = doc_content.find(heading)
        if start == -1:
            continue
        end = start + len(heading)
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end + 1},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        })

    return requests


def export_prd_to_doc(prd: dict, folder_id: str | None = None) -> dict:
    """
    Create a Google Doc from a PRD dict.

    Args:
        prd: the Executor's PRD output (prd field from agent JSON)
        folder_id: optional Google Drive folder ID to place the doc in

    Returns:
        {"doc_id": str, "doc_url": str, "title": str}
    """
    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    title = prd.get("title", "Untitled PRD")

    # 1. Create empty document
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

    log.info("Created Google Doc: %s (%s)", title, doc_url)

    # 2. Insert PRD content
    insert_requests = _build_prd_requests(prd)
    if insert_requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": insert_requests},
        ).execute()

    # 3. Re-read document to get final text positions, then apply heading styles
    updated_doc = docs_service.documents().get(documentId=doc_id).execute()
    full_text = ""
    for element in updated_doc.get("body", {}).get("content", []):
        para = element.get("paragraph", {})
        for run in para.get("elements", []):
            text_run = run.get("textRun", {})
            full_text += text_run.get("content", "")

    style_requests = _build_heading_style_requests(full_text)
    if style_requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": style_requests},
        ).execute()

    # 4. Move to folder if specified
    if folder_id:
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            fields="id, parents",
        ).execute()
        log.info("Moved doc to folder: %s", folder_id)

    return {"doc_id": doc_id, "doc_url": doc_url, "title": title}
