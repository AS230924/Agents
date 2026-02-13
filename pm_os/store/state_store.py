"""
SQLite-backed state store for session and turn tracking.
"""

import json
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "pm_os.db"


def _get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    """Create tables if they don't exist."""
    conn = _get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                problem_state TEXT DEFAULT 'undefined',
                decision_state TEXT DEFAULT 'none'
            );

            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                turn_number INTEGER,
                query TEXT,
                intent TEXT,
                sequence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_session(db_path: str | Path | None = None) -> str:
    """Create a new session and return its id."""
    init_db(db_path)
    session_id = uuid.uuid4().hex[:12]
    conn = _get_connection(db_path)
    try:
        conn.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))
        conn.commit()
    finally:
        conn.close()
    return session_id


def get_session(session_id: str, db_path: str | Path | None = None) -> dict | None:
    """Return session row as dict, or None."""
    init_db(db_path)
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, problem_state, decision_state FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def update_session_state(
    session_id: str,
    problem_state: str | None = None,
    decision_state: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Update problem_state and/or decision_state for a session."""
    init_db(db_path)
    conn = _get_connection(db_path)
    try:
        if problem_state is not None:
            conn.execute(
                "UPDATE sessions SET problem_state = ? WHERE id = ?",
                (problem_state, session_id),
            )
        if decision_state is not None:
            conn.execute(
                "UPDATE sessions SET decision_state = ? WHERE id = ?",
                (decision_state, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def add_turn(
    session_id: str,
    query: str,
    intent: str,
    sequence: list[str],
    db_path: str | Path | None = None,
) -> int:
    """Record a turn and return the turn number."""
    init_db(db_path)
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COALESCE(MAX(turn_number), 0) AS max_turn FROM turns WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        turn_number = row["max_turn"] + 1
        conn.execute(
            "INSERT INTO turns (session_id, turn_number, query, intent, sequence) VALUES (?, ?, ?, ?, ?)",
            (session_id, turn_number, query, intent, json.dumps(sequence)),
        )
        conn.commit()
        return turn_number
    finally:
        conn.close()


def get_prior_turns(
    session_id: str, limit: int = 10, db_path: str | Path | None = None
) -> list[dict]:
    """Return the last `limit` turns for a session."""
    init_db(db_path)
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT turn_number, query, intent, sequence FROM turns WHERE session_id = ? ORDER BY turn_number DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["sequence"] = json.loads(d["sequence"])
            results.append(d)
        return list(reversed(results))
    finally:
        conn.close()
