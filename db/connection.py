import sqlite3

from config import DATA_DIR

DB_PATH = DATA_DIR / "listbot.db"

def get_connection() -> sqlite3.Connection:
    """Open a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
