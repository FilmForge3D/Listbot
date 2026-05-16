#!/usr/bin/env python3
"""Import prompts from ergebnis.json into the ListBot SQLite database."""

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
import db
import db.connection as _db_conn

_DEFAULT_DB = Path(__file__).parent / "listbot.db"


def _build_user_maps(user_lookup: dict[str, str]) -> tuple[dict[int, str], dict[str, int]]:
    """Deduplicate user_lookup keeping the longer name per user_id.

    Returns (id_to_name, name_to_id).
    """
    id_to_name: dict[int, str] = {}
    for name, uid_str in user_lookup.items():
        if not uid_str:
            continue
        uid = int(uid_str)
        if uid not in id_to_name or len(name) > len(id_to_name[uid]):
            id_to_name[uid] = name
    name_to_id = {name: uid for uid, name in id_to_name.items()}
    return id_to_name, name_to_id


def import_json(json_path: Path, db_path: Path) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    chat_id: int = data["chat_id"]
    chat_name: str = data["chat_name"]
    list_names: dict[str, str] = data.get("list_names", {"1": "list1", "2": "list2", "3": "list3"})
    prompts: list[dict] = data["prompts"]
    user_lookup: dict[str, str] = data.get("user_lookup", {})

    _db_conn.DB_PATH = db_path
    db.init_db()

    id_to_name, name_to_id = _build_user_maps(user_lookup)

    with db.get_connection() as conn:
        for uid, name in id_to_name.items():
            conn.execute(
                "INSERT INTO users (user_id, name) VALUES (?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET name = excluded.name",
                (uid, name),
            )

        conn.execute("INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,))

        list_id_map: dict[int, int] = {}
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

            uid_str = p.get("user_id") or user_lookup.get(p.get("first_name", ""), "")
            added_by_id: int | None = int(uid_str) if uid_str else name_to_id.get(p.get("first_name", ""))

            image_path: str | None = p.get("image_path")
            media_file_id: str | None = image_path
            media_type: str | None = "photo" if image_path else None
            raw_text = p["prompt"]
            # Pure photo (no caption): filename == prompt text → store NULL
            is_caption = not image_path or Path(image_path).name != raw_text
            text: str | None = raw_text if is_caption else None

            pos = position_counters[list_num]
            position_counters[list_num] += 1
            conn.execute(
                """INSERT OR REPLACE INTO prompts
                   (list_id, position, text, media_file_id, media_type, drawn, drawn_at, added_by_id, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (list_id, pos, text, media_file_id, media_type, p.get("draw_count", 0), p.get("last_drawn"), added_by_id, p.get("date")),
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
    parser.add_argument("input", nargs="?", default=str(Path(__file__).parent / "ergebnis.json"), help="Path to ergebnis.json (default: ergebnis.json in script folder)")
    parser.add_argument("--db", default=str(_DEFAULT_DB), help="Path to SQLite database file")
    args = parser.parse_args()

    json_path = Path(args.input)
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        raise SystemExit(1)

    import_json(json_path, Path(args.db))


if __name__ == "__main__":
    main()
