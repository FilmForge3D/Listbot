from db.connection import get_connection


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
