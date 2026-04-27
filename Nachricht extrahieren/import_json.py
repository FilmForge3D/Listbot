#!/usr/bin/env python3
"""Import prompts from ergebnis.json into the ListBot SQLite database."""

import json
import sys
import argparse
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
import database  # noqa: E402

_DEFAULT_DB = Path(__file__).parent / "listbot.db"


def import_json(json_path: Path, db_path: Path) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    chat_id: int = data["chat_id"]
    chat_name: str = data["chat_name"]
    list_names: dict[str, str] = data.get("list_names", {"1": "list1", "2": "list2", "3": "list3"})
    prompts: list[dict] = data["prompts"]

    database.DB_PATH = db_path
    database.init_db()

    list_id_map: dict[int, int] = {}
    with database.get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,))

        for num_str, name in list_names.items():
            cur = conn.execute(
                "INSERT OR IGNORE INTO lists (chat_id, list_name) VALUES (?, ?)",
                (chat_id, name),
            )
            if cur.lastrowid:
                list_id_map[int(num_str)] = cur.lastrowid
            else:
                row = conn.execute(
                    "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
                    (chat_id, name),
                ).fetchone()
                list_id_map[int(num_str)] = row["id"]

        position_counters: dict[int, int] = {k: 1 for k in list_id_map}
        inserted = skipped = 0

        for p in prompts:
            list_num = p.get("list_number", 1)
            list_id = list_id_map.get(list_num)
            if list_id is None:
                skipped += 1
                continue
            pos = position_counters[list_num]
            position_counters[list_num] += 1
            conn.execute(
                """INSERT OR REPLACE INTO prompts
                   (list_id, position, text, drawn, drawn_at, added_by_name, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (list_id, pos, p["prompt"], p.get("draw_count", 0), p.get("last_drawn"), p.get("first_name"), p.get("date")),
            )
            inserted += 1

        conn.commit()

    print(f"Chat: {chat_name} (ID {chat_id})")
    for num_str, name in list_names.items():
        count = sum(1 for p in prompts if p.get("list_number", 1) == int(num_str))
        print(f"  List {num_str} ({name}): {count} prompts")
    print(f"Inserted: {inserted}, skipped: {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import ergebnis.json into the ListBot SQLite database")
    parser.add_argument("input", nargs="?", default="ergebnis.json", help="Path to ergebnis.json")
    parser.add_argument("--db", default=str(_DEFAULT_DB), help="Path to SQLite database file")
    args = parser.parse_args()

    json_path = Path(args.input)
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        raise SystemExit(1)

    import_json(json_path, Path(args.db))


if __name__ == "__main__":
    main()
