import random
import sqlite3

from db.connection import get_connection
from db.lists import _get_or_create_list


def add_prompt(chat_id: int, list_name: str, text: str, added_by_id: int | None = None) -> int:
    """Append a prompt to a list. Returns the new prompt's position."""
    with get_connection() as conn:
        list_id = _get_or_create_list(conn, chat_id, list_name)
        max_pos: int = conn.execute(
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
        prompt: sqlite3.Row = random.choices(prompts, weights=weights, k=1)[0]
        conn.execute(
            "UPDATE prompts SET drawn = drawn + 1, drawn_at = datetime('now') WHERE id = ?",
            (prompt["id"],),
        )
        conn.commit()
        return prompt


def get_recently_drawn_prompts(
    chat_id: int, list_name: str, limit: int = 10, max_age_days: int = 7
) -> list[sqlite3.Row]:
    """Return up to `limit` prompts drawn within the last `max_age_days` days, most recent first."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return []
        return conn.execute(
            "SELECT text, drawn_at FROM prompts"
            " WHERE list_id = ? AND drawn_at IS NOT NULL"
            " AND drawn_at >= datetime('now', ?)"
            " ORDER BY drawn_at DESC LIMIT ?",
            (row["id"], f"-{max_age_days} days", limit),
        ).fetchall()


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
