#!/usr/bin/env python3
"""SQLite database layer for ListBot prompt storage."""

import sqlite3
import logging
import os
import random
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(os.environ.get("DATA_DIR", ".")) / "listbot.db"


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
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name    TEXT    NOT NULL
            )
        """)
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
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id      INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
                position     INTEGER NOT NULL,
                text         TEXT    NOT NULL,
                drawn        INTEGER NOT NULL DEFAULT 0,
                drawn_at     TEXT,
                added_by_id  INTEGER REFERENCES users(user_id),
                added_at     TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (list_id, position)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id      INTEGER PRIMARY KEY,
                default_list TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS list_shares (
                list_id       INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
                guest_chat_id INTEGER NOT NULL,
                PRIMARY KEY (list_id, guest_chat_id)
            )
        """)
        try:
            conn.execute("ALTER TABLE prompts ADD COLUMN added_by_id INTEGER REFERENCES users(user_id)")
        except Exception:
            pass
        conn.commit()
    logger.info("Database initialised at %s", DB_PATH)


def get_default_list(chat_id: int) -> str | None:
    """Return the default list name for a chat, or None if not set."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT default_list FROM chat_settings WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return row["default_list"] if row else None


def set_default_list(chat_id: int, list_name: str) -> None:
    """Persist the default list for a chat, creating or overwriting the setting."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_settings (chat_id, default_list) VALUES (?, ?)"
            " ON CONFLICT(chat_id) DO UPDATE SET default_list = excluded.default_list",
            (chat_id, list_name),
        )
        conn.commit()


def upsert_user(user_id: int, name: str) -> None:
    """Insert or update a user's display name."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (user_id, name) VALUES (?, ?)"
            " ON CONFLICT(user_id) DO UPDATE SET name = excluded.name",
            (user_id, name),
        )
        conn.commit()


def lookup_name(entity_id: int) -> str | None:
    """Return the stored name for a user or chat ID, or None if unknown."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM users WHERE user_id = ?", (entity_id,)
        ).fetchone()
        return row["name"] if row else None


def add_list_share(list_id: int, guest_chat_id: int) -> bool:
    """Add a guest chat to a list's shares. Returns False if already shared."""
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO list_shares (list_id, guest_chat_id) VALUES (?, ?)",
                (list_id, guest_chat_id),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_list_share(list_id: int, guest_chat_id: int) -> bool:
    """Remove a guest chat from a list's shares. Returns False if not found."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM list_shares WHERE list_id = ? AND guest_chat_id = ?",
            (list_id, guest_chat_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_list_shares(list_id: int) -> list[int]:
    """Return guest chat_ids that have access to a list."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT guest_chat_id FROM list_shares WHERE list_id = ?",
            (list_id,),
        ).fetchall()
        return [row["guest_chat_id"] for row in rows]


def transfer_list_ownership(list_id: int, new_owner_chat_id: int) -> bool:
    """Transfer ownership of a list to a guest. Old owner becomes a guest.
    Returns False if list not found or new owner is already the owner."""
    with get_connection() as conn:
        row = conn.execute("SELECT chat_id FROM lists WHERE id = ?", (list_id,)).fetchone()
        if not row:
            return False
        old_owner = row["chat_id"]
        if old_owner == new_owner_chat_id:
            return False
        conn.execute("UPDATE lists SET chat_id = ? WHERE id = ?", (new_owner_chat_id, list_id))
        conn.execute(
            "INSERT OR IGNORE INTO list_shares (list_id, guest_chat_id) VALUES (?, ?)",
            (list_id, old_owner),
        )
        conn.execute(
            "DELETE FROM list_shares WHERE list_id = ? AND guest_chat_id = ?",
            (list_id, new_owner_chat_id),
        )
        conn.commit()
        return True


def get_shared_lists(chat_id: int) -> list[dict]:
    """Return lists shared with this chat (not owned by it)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT l.id AS list_id, l.list_name, l.chat_id AS owner_chat_id"
            " FROM list_shares s JOIN lists l ON s.list_id = l.id"
            " WHERE s.guest_chat_id = ? ORDER BY l.list_name",
            (chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def resolve_list_owner(accessing_chat_id: int, list_name: str) -> int | None:
    """Return the owner chat_id for a list accessible by accessing_chat_id.
    Checks owned lists first, then lists shared with this chat."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (accessing_chat_id, list_name),
        ).fetchone()
        if row:
            return accessing_chat_id
        row = conn.execute(
            "SELECT l.chat_id FROM lists l JOIN list_shares s ON l.id = s.list_id"
            " WHERE s.guest_chat_id = ? AND l.list_name = ?",
            (accessing_chat_id, list_name),
        ).fetchone()
        return row["chat_id"] if row else None


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


def add_prompt(chat_id: int, list_name: str, text: str, added_by_id: int | None = None) -> int:
    """Append a prompt to a list. Returns the new prompt's position."""
    with get_connection() as conn:
        list_id = _get_or_create_list(conn, chat_id, list_name)
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), 0) FROM prompts WHERE list_id = ?",
            (list_id,),
        ).fetchone()[0]
        position = max_pos + 1
        conn.execute(
            "INSERT INTO prompts (list_id, position, text, added_by_id) VALUES (?, ?, ?, ?)",
            (list_id, position, text, added_by_id),
        )
        conn.commit()
        return position


def get_prompts(chat_id: int, list_name: str) -> list[sqlite3.Row]:
    """Return all prompts for a list ordered by position."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return []
        return conn.execute(
            "SELECT * FROM prompts WHERE list_id = ? ORDER BY position",
            (row["id"],),
        ).fetchall()


def draw_random_prompt(chat_id: int, list_name: str) -> sqlite3.Row | None:
    """Pick a weighted-random prompt and increment its draw count. Returns None if list is empty.

    Weight = 1 / (draw_count + 1), so each draw lowers the probability of being picked again.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return None
        list_id = row["id"]
        prompts = conn.execute(
            "SELECT p.*, u.name AS added_by_name FROM prompts p"
            " LEFT JOIN users u ON p.added_by_id = u.user_id"
            " WHERE p.list_id = ? ORDER BY p.position",
            (list_id,),
        ).fetchall()
        if not prompts:
            return None
        weights = [1.0 / (p["drawn"] + 1) for p in prompts]
        prompt = random.choices(prompts, weights=weights, k=1)[0]
        conn.execute(
            "UPDATE prompts SET drawn = drawn + 1, drawn_at = datetime('now') WHERE id = ?",
            (prompt["id"],),
        )
        conn.commit()
        return prompt


def get_stats(chat_id: int, list_name: str) -> dict | None:
    """Return statistics for a list, or None if the list does not exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return None
        list_id = row["id"]
        total = conn.execute(
            "SELECT COUNT(*) FROM prompts WHERE list_id = ?", (list_id,)
        ).fetchone()[0]
        total_draws = conn.execute(
            "SELECT COALESCE(SUM(drawn), 0) FROM prompts WHERE list_id = ?", (list_id,)
        ).fetchone()[0]
        never_drawn = conn.execute(
            "SELECT COUNT(*) FROM prompts WHERE list_id = ? AND drawn = 0", (list_id,)
        ).fetchone()[0]
        most_drawn = conn.execute(
            "SELECT text, drawn FROM prompts WHERE list_id = ? ORDER BY drawn DESC LIMIT 1",
            (list_id,),
        ).fetchone()
        by_user = conn.execute(
            "SELECT COALESCE(u.name, 'Unknown') AS name, COUNT(*) AS cnt"
            " FROM prompts p LEFT JOIN users u ON p.added_by_id = u.user_id"
            " WHERE p.list_id = ? GROUP BY p.added_by_id ORDER BY cnt DESC",
            (list_id,),
        ).fetchall()
        return {
            "total": total,
            "total_draws": total_draws,
            "never_drawn": never_drawn,
            "most_drawn": {"text": most_drawn["text"], "count": most_drawn["drawn"]} if most_drawn else None,
            "by_user": [{"name": r["name"], "count": r["cnt"]} for r in by_user],
        }


def edit_prompt(chat_id: int, list_name: str, position: int, new_text: str) -> bool:
    """Update the text of a prompt by 1-based position. Returns True if a row was updated."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return False
        list_id = row["id"]
        cur = conn.execute(
            "UPDATE prompts SET text = ? WHERE list_id = ? AND position = ?",
            (new_text, list_id, position),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_list(chat_id: int, list_name: str) -> bool:
    """Delete a list only if it has no prompts. Returns True on success, False otherwise."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return False
        count = conn.execute(
            "SELECT COUNT(*) FROM prompts WHERE list_id = ?", (row["id"],)
        ).fetchone()[0]
        if count > 0:
            return False
        conn.execute("DELETE FROM lists WHERE id = ?", (row["id"],))
        conn.commit()
        return True


def rename_list(chat_id: int, old_name: str, new_name: str) -> bool:
    """Rename a list, updating the default setting if needed. Returns False if not found or name taken."""
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM lists WHERE chat_id=? AND list_name=?", (chat_id, old_name)).fetchone()
        if not row:
            return False
        if conn.execute("SELECT id FROM lists WHERE chat_id=? AND list_name=?", (chat_id, new_name)).fetchone():
            return False
        conn.execute("UPDATE lists SET list_name=? WHERE id=?", (new_name, row["id"]))
        conn.execute(
            "UPDATE chat_settings SET default_list=? WHERE chat_id=? AND default_list=?",
            (new_name, chat_id, old_name),
        )
        conn.commit()
        return True


def remove_prompt(chat_id: int, list_name: str, position: int) -> dict | None:
    """Remove a prompt by 1-based position. Returns the deleted prompt dict or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return None
        list_id = row["id"]
        prompt = conn.execute(
            "SELECT text FROM prompts WHERE list_id = ? AND position = ?",
            (list_id, position),
        ).fetchone()
        if not prompt:
            return None
        conn.execute(
            "DELETE FROM prompts WHERE list_id = ? AND position = ?",
            (list_id, position),
        )
        conn.commit()
        return {"text": prompt["text"]}
