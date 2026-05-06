from db.connection import get_connection


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
