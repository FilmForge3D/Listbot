#!/usr/bin/env python3
"""SQLite database layer for ListBot prompt storage."""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("listbot.db")


def get_connection() -> sqlite3.Connection:
    """Open a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they do not exist yet."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lists (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                list_name  TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (chat_id, list_name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id    INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
                position   INTEGER NOT NULL,
                text       TEXT    NOT NULL,
                drawn      INTEGER NOT NULL DEFAULT 0,
                drawn_at   TEXT,
                added_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (list_id, position)
            )
        """)
        conn.commit()
    logger.info("Database initialised at %s", DB_PATH)


def _get_or_create_list(conn: sqlite3.Connection, chat_id: int, list_name: str) -> int:
    """Return the list row id, creating the row if needed."""
    row = conn.execute(
        "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
        (chat_id, list_name),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO lists (chat_id, list_name) VALUES (?, ?)",
        (chat_id, list_name),
    )
    return cur.lastrowid


def get_list_names(chat_id: int) -> list[str]:
    """Return all list names for a chat, sorted alphabetically."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT list_name FROM lists WHERE chat_id = ? ORDER BY list_name",
            (chat_id,),
        ).fetchall()
        return [row["list_name"] for row in rows]


def add_prompt(chat_id: int, list_name: str, text: str) -> int:
    """Append a prompt to a list. Returns the new prompt id."""
    with get_connection() as conn:
        list_id = _get_or_create_list(conn, chat_id, list_name)
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), 0) FROM prompts WHERE list_id = ?",
            (list_id,),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO prompts (list_id, position, text) VALUES (?, ?, ?)",
            (list_id, max_pos + 1, text),
        )
        conn.commit()
        return cur.lastrowid


def get_prompts(chat_id: int, list_name: str) -> list[sqlite3.Row]:
    """Return all prompts for a list ordered by position."""
    with get_connection() as conn:
        list_id = _get_or_create_list(conn, chat_id, list_name)
        conn.commit()
        return conn.execute(
            "SELECT * FROM prompts WHERE list_id = ? ORDER BY position",
            (list_id,),
        ).fetchall()


def draw_random_prompt(chat_id: int, list_name: str) -> sqlite3.Row | None:
    """Pick a random undrawn prompt, mark it drawn, and return it. Returns None if all drawn."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return None
        list_id = row["id"]
        prompt = conn.execute(
            "SELECT * FROM prompts WHERE list_id = ? AND drawn = 0 ORDER BY RANDOM() LIMIT 1",
            (list_id,),
        ).fetchone()
        if not prompt:
            return None
        conn.execute(
            "UPDATE prompts SET drawn = 1, drawn_at = datetime('now') WHERE id = ?",
            (prompt["id"],),
        )
        conn.commit()
        return prompt


def remove_prompt(chat_id: int, list_name: str, position: int) -> bool:
    """Remove a prompt by 1-based position. Returns True if a row was deleted."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return False
        list_id = row["id"]
        cur = conn.execute(
            "DELETE FROM prompts WHERE list_id = ? AND position = ?",
            (list_id, position),
        )
        conn.commit()
        return cur.rowcount > 0
