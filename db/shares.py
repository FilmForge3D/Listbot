import sqlite3

from db.connection import get_connection


def add_list_share(list_id: int, guest_chat_id: int) -> bool:
    """Add a guest chat to a list's shares. Returns False if already shared."""
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO list_shares (list_id, guest_chat_id) VALUES (?, ?)",
                (list_id, guest_chat_id),
            )
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
        return cur.rowcount > 0


def get_list_shares(list_id: int) -> list[int]:
    """Return guest chat_ids that have access to a list."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT guest_chat_id FROM list_shares WHERE list_id = ?",
            (list_id,),
        ).fetchall()
        return [row["guest_chat_id"] for row in rows]


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
        return True


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
