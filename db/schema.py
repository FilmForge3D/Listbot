import logging

from db.connection import get_connection

logger = logging.getLogger(__name__)


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
    from db.connection import DB_PATH
    logger.info("Database initialised at %s", DB_PATH)
