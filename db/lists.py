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


def create_list(chat_id: int, list_name: str) -> int:
    """Create a list if it doesn't exist and return its id."""
    with get_connection() as conn:
        return _get_or_create_list(conn, chat_id, list_name)


def get_list_id(chat_id: int, list_name: str) -> int | None:
    """Return the id for a named list, or None if it does not exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (chat_id, list_name),
        ).fetchone()
    return int(row["id"]) if row else None


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
    list_id = get_list_id(chat_id, old_name)
    if list_id is None:
        return False
    if get_list_id(chat_id, new_name) is not None:
        return False
    with get_connection() as conn:
        conn.execute("UPDATE lists SET list_name = ? WHERE id = ?", (new_name, list_id))
        conn.execute(
            "UPDATE chat_settings SET default_list = ? WHERE chat_id = ? AND default_list = ?",
            (new_name, chat_id, old_name),
        )
    return True


def delete_list(chat_id: int, list_name: str) -> bool:
    """Delete a list only if it has no prompts. Returns True on success, False otherwise."""
    list_id = get_list_id(chat_id, list_name)
    if list_id is None:
        return False
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM prompts WHERE list_id = ?", (list_id,)).fetchone()[0]
        if count > 0:
            return False
        conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
    return True
