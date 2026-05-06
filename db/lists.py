import sqlite3

from db.connection import get_connection


def _get_or_create_list(conn: sqlite3.Connection, chat_id: int, list_name: str) -> int:
    """Return the list row id, creating the row if needed."""
    row = conn.execute(
        "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
        (chat_id, list_name),
    ).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO lists (chat_id, list_name) VALUES (?, ?)",
        (chat_id, list_name),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def get_list_names(chat_id: int) -> list[str]:
    """Return all list names for a chat, sorted alphabetically."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT list_name FROM lists WHERE chat_id = ? ORDER BY list_name",
            (chat_id,),
        ).fetchall()
        return [row["list_name"] for row in rows]


def rename_list(chat_id: int, old_name: str, new_name: str) -> bool:
    """Rename a list, updating the default setting if needed. Returns False if not found or name taken."""
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM lists WHERE chat_id = ? AND list_name = ?", (chat_id, old_name)).fetchone()
        if not row:
            return False
        if conn.execute("SELECT id FROM lists WHERE chat_id = ? AND list_name = ?", (chat_id, new_name)).fetchone():
            return False
        conn.execute("UPDATE lists SET list_name = ? WHERE id = ?", (new_name, row["id"]))
        conn.execute(
            "UPDATE chat_settings SET default_list = ? WHERE chat_id = ? AND default_list = ?",
            (new_name, chat_id, old_name),
        )
        return True


def delete_list(chat_id: int, list_name: str) -> bool:
    """Delete a list only if it has no prompts. Returns True on success, False otherwise."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
        if not row:
            return False
        count = conn.execute("SELECT COUNT(*) FROM prompts WHERE list_id = ?", (row["id"],)).fetchone()[0]
        if count > 0:
            return False
        conn.execute("DELETE FROM lists WHERE id = ?", (row["id"],))
        return True
