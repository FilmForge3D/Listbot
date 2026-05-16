#!/usr/bin/env python3
"""
Extrahiert aus einem Telegram-Gruppenexport (result.json):
  1. Relevante Nachrichten von ListBot (drew/added the following, hat X gegruppt)
  2. Nachrichten die mit / beginnen
"""

import argparse
import json
import re
import shutil
from collections import Counter
from difflib import get_close_matches
from pathlib import Path
from typing import Any, cast

_SCRIPT_DIR = Path(__file__).parent

# Muster für relevante ListBot-Nachrichten
LISTBOT_PATTERNS = [
    (re.compile(r"^.+\s+added the following:", re.IGNORECASE), "added"),
    (re.compile(r"^.+ successfully added '.+' in position \d+ to the list\.", re.IGNORECASE), "added"),
    (re.compile(r"^✅ .+ added \d+: '.+'"), "added"),
    (re.compile(r"^Successfully added '.+' in position", re.IGNORECASE), "added"),
    (re.compile(r"^Successfully added '.+' to the list\.", re.IGNORECASE), "added"),
    (re.compile(r"^\d+: .+"), "drew"),
    (re.compile(r"^.+\s+drew the following:", re.IGNORECASE), "drew"),
    (re.compile(r"^.+ successfully changed position \d+ from '.+' into '.+'", re.IGNORECASE), "edited"),
    (re.compile(r"^✅ .+ changed \d+ from '.+' to '.+'"), "edited"),
    (re.compile(r"^.+\s+hat\s+.+\s+gegruppt", re.IGNORECASE), "gruppt"),
]


def match_listbot(text: str) -> str | None:
    """Gibt den Match-Typ zurück oder None wenn keine Übereinstimmung."""
    for pattern, label in LISTBOT_PATTERNS:
        if pattern.search(text):
            return label
    return None


def get_text(message: dict) -> str:
    """Gibt den reinen Text einer Nachricht zurück (auch bei Entities)."""
    content = message.get("text", "")
    if isinstance(content, list):
        return "".join(part if isinstance(part, str) else part.get("text", "") for part in content)
    return str(content)


def load_json_tolerant(path: Path) -> dict[str, Any]:
    """Lädt JSON – bei Fehler wird json_repair als Fallback versucht."""
    raw = path.read_text(encoding="utf-8")
    try:
        return cast(dict[str, Any], json.loads(raw))
    except json.JSONDecodeError as e:
        print(f"Warnung: JSON-Fehler ({e}), versuche automatische Reparatur …")
        try:
            from json_repair import repair_json

            data = cast(dict[str, Any], json.loads(repair_json(raw)))
            print("Reparatur erfolgreich.")
            return data
        except ImportError:
            print("Tipp: Installiere json_repair für automatische Reparatur:\n  pip install json-repair\n")
            raise


_ADD_EDIT_COMMANDS = ["add", "grupp", "edit"]

_POS_PATTERNS = [
    re.compile(r"als\s+(\d+)\.\s+gegruppt", re.IGNORECASE),
    re.compile(r"added\s+(\d+):", re.IGNORECASE),
    re.compile(r"in position\s+(\d+)", re.IGNORECASE),
    re.compile(r"changed position\s+(\d+)", re.IGNORECASE),
    re.compile(r"changed\s+(\d+)\s+from", re.IGNORECASE),
]


def _is_add_edit_cmd(text: str) -> bool:
    cmd = text.split()[0].lstrip("/").rstrip("23")
    return bool(get_close_matches(cmd, _ADD_EDIT_COMMANDS, n=1, cutoff=0.6))


def _extract_position(text: str) -> int | None:
    for pat in _POS_PATTERNS:
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None


def _parse_list_number(cmd: str) -> int:
    """Returns 1, 2, or 3 from a command like /add2, /grupp3, /edit."""
    cmd = cmd.lstrip("/").split("@")[0]
    if cmd.endswith("2"):
        return 2
    if cmd.endswith("3"):
        return 3
    return 1


def _parse_add_prompt(text: str) -> tuple[str | None, int]:
    """Extracts (prompt, list_number) from a /add or /grupp slash command text."""
    parts = text.split(None, 1)
    if len(parts) < 2:
        return None, 1
    return parts[1].strip(), _parse_list_number(parts[0])


_LISTBOT_ENTRY_PATTERNS: list[tuple[re.Pattern, int | None, int]] = [
    (re.compile(r"^(\w+)\s+hat\s+'(.+?)'\s+als\s+\d+\.\s+gegruppt", re.IGNORECASE), 1, 2),
    (re.compile(r"^(\w+)\s+successfully added '(.+?)'\s+in position", re.IGNORECASE), 1, 2),
    (re.compile(r"^Successfully added '(.+?)'\s+in position", re.IGNORECASE), None, 1),
    (re.compile(r"^Successfully added '(.+?)' to the list", re.IGNORECASE), None, 1),
    (re.compile(r"^✅ (\w+) added \d+: '(.+?)'(?!\w)"), 1, 2),
    (re.compile(r"^(\w+)\s+successfully changed position \d+ from '.+?'(?!\w) into '(.+?)'(?!\w)", re.IGNORECASE), 1, 2),
    (re.compile(r"^✅ (\w+) changed \d+ from '.+?'(?!\w) to '(.+?)'(?!\w)"), 1, 2),
]


def _parse_listbot_entry(text: str) -> tuple[str | None, str | None]:
    """Returns (first_name, prompt) extracted from a listbot added/gruppt/edited message."""
    for pattern, name_group, prompt_group in _LISTBOT_ENTRY_PATTERNS:
        m = pattern.search(text)
        if m:
            name = m.group(name_group) if name_group else None
            return name, m.group(prompt_group)
    return None, None


def _is_draw_result(text: str) -> bool:
    """Returns True if the drew message is an actual draw, not a /list output.

    /list outputs have sequentially numbered lines (1,2,3… or 5,6,7…).
    Draw results are single-line or have non-sequential numbering.
    """
    lines = [line for line in text.strip().split("\n") if line.strip()]
    if len(lines) <= 1:
        return True
    numbers = []
    for line in lines:
        m = re.match(r"^(\d+):", line)
        if not m:
            return True
        numbers.append(int(m.group(1)))
    return any(numbers[i + 1] != numbers[i] + 1 for i in range(len(numbers) - 1))


def _extract_drew_prompts(text: str) -> list[str]:
    """Extracts prompt texts from the numbered lines of a draw result message."""
    prompts = []
    for line in text.strip().split("\n"):
        m = re.match(r"^\d+:\s*(.+)", line.strip())
        if m:
            prompts.append(m.group(1).strip())
    return prompts


_ADD_CMD_BASES = {"add", "grupp"}


def normalize_prompts(result: dict) -> dict:
    """Transforms raw extracted data into a single normalized prompts list."""
    user_lookup: dict[str, str] = result.get("user_lookup", {})
    draw_counts: dict[str, int] = {}
    last_drawn: dict[str, str] = {}
    for msg in result["listbot"]:
        if msg["match_type"] == "drew" and _is_draw_result(msg["text"]):
            for p in _extract_drew_prompts(msg["text"]):
                key = p.strip().lower()
                draw_counts[key] = draw_counts.get(key, 0) + 1
                last_drawn[key] = msg["date"]

    prompts = []
    for msg in result["slash_commands"]:
        cmd_base = msg["text"].split()[0].lstrip("/").split("@")[0].rstrip("23")
        if cmd_base not in _ADD_CMD_BASES:
            continue
        prompt, list_number = _parse_add_prompt(msg["text"])
        if not prompt:
            continue
        full_name = msg["from"]
        fname = full_name.split()[0]
        entry: dict = {
            "date": msg["date"],
            "first_name": fname,
            "user_id": user_lookup.get(full_name) or user_lookup.get(fname) or "",
            "prompt": prompt,
            "list_number": list_number,
            "draw_count": draw_counts.get(prompt.strip().lower(), 0),
            "last_drawn": last_drawn.get(prompt.strip().lower()),
        }
        if msg.get("image_path"):
            entry["image_path"] = msg["image_path"]
        prompts.append(entry)

    for msg in result["listbot"]:
        if msg["match_type"] not in {"added", "gruppt", "edited"}:
            continue
        first_name, prompt = _parse_listbot_entry(msg["text"])
        if not prompt:
            continue
        fname = first_name or "unknown"
        prompts.append(
            {
                "date": msg["date"],
                "first_name": fname,
                "user_id": user_lookup.get(fname, ""),
                "prompt": prompt,
                "list_number": 1,
                "draw_count": draw_counts.get(prompt.strip().lower(), 0),
                "last_drawn": last_drawn.get(prompt.strip().lower()),
            }
        )

    prompts.sort(key=lambda x: x["date"])
    return {
        "chat_id": result["chat_id"],
        "chat_name": result["chat_name"],
        "list_names": {"1": "list1", "2": "list2", "3": "list3"},
        "user_lookup": result.get("user_lookup", {}),
        "prompts": prompts,
    }


def extract_messages(input_path: Path, bot_name: str = "ListBot") -> dict:
    data = load_json_tolerant(input_path)

    messages = data.get("messages", [])

    listbot_msgs = []
    slash_msgs = []

    for msg in messages:
        if msg.get("type") != "message":
            continue

        sender = msg.get("from", "") or ""
        text = get_text(msg)
        timestamp = msg.get("date", "")
        msg_id = msg.get("id", "")

        entry = {
            "id": msg_id,
            "date": timestamp,
            "from": sender,
            "text": text,
        }

        if sender == bot_name:
            match_type = match_listbot(text)
            if match_type:
                listbot_msgs.append({**entry, "match_type": match_type})

        is_add_cmd = (
            text.strip().startswith("/")
            and text.strip().split()[0].lstrip("/").split("@")[0].rstrip("23") in _ADD_CMD_BASES
        )
        media = msg.get("photo", "") or msg.get("file", "")
        if media and is_add_cmd:
            src = input_path.parent / media
            dest_dir = input_path.parent / "prompt_images"
            dest_dir.mkdir(exist_ok=True)
            filename = Path(media).name
            dest = dest_dir / filename
            if src.exists():
                shutil.copy2(src, dest)
            cmd_token = text.strip().split()[0]
            entry_text = text if len(text.split()) > 1 else f"{cmd_token} {filename}"
            slash_msgs.append({**entry, "text": entry_text, "image_path": f"media/{filename}"})
        elif text.startswith("/"):
            slash_msgs.append(entry)

    # Deduplizierung: ListBot added/gruppt/edited-Nachrichten entfernen,
    # wenn ein /add- oder /edit-Befehl in einem Fenster von MSG_WINDOW IDs davor liegt
    MSG_WINDOW = 5
    OVERLAP_TYPES = {"added", "gruppt", "edited"}
    slash_ids = {msg["id"] for msg in slash_msgs if _is_add_edit_cmd(msg["text"])}
    listbot_msgs = [
        msg
        for msg in listbot_msgs
        if msg["match_type"] not in OVERLAP_TYPES
        or not any((msg["id"] - w) in slash_ids for w in range(1, MSG_WINDOW + 1))
    ]

    # Deduplizierung: added/gruppt entfernen wenn ein späteres edit dieselbe Position betrifft;
    # bei mehreren edits nur den letzten behalten
    edited_positions = {_extract_position(msg["text"]) for msg in listbot_msgs if msg["match_type"] == "edited"} - {
        None
    }
    seen_edited: set[int] = set()
    merged: list[dict] = []
    for msg in reversed(listbot_msgs):
        pos = _extract_position(msg["text"])
        if msg["match_type"] == "edited":
            if pos in seen_edited:
                continue
            if pos is not None:
                seen_edited.add(pos)
        elif msg["match_type"] in {"added", "gruppt"} and pos in edited_positions:
            continue
        merged.append(msg)
    listbot_msgs = list(reversed(merged))

    user_lookup: dict[str, str] = {}
    for msg in messages:
        if msg.get("type") != "message":
            continue
        name = msg.get("from", "") or ""
        raw_id = msg.get("from_id", "") or ""
        uid = raw_id.removeprefix("user")
        if name and uid:
            user_lookup[name] = uid

    for msg in listbot_msgs:
        first_name, _ = _parse_listbot_entry(msg["text"])
        if first_name and first_name not in user_lookup:
            inherited = next(
                (uid for name, uid in user_lookup.items() if name.split()[0] == first_name and uid),
                "",
            )
            user_lookup[first_name] = inherited

    chat_id = data.get("id")
    chat_name = data.get("name", "")
    return {
        "chat_id": chat_id,
        "chat_name": chat_name,
        "listbot": listbot_msgs,
        "slash_commands": slash_msgs,
        "user_lookup": user_lookup,
    }


def print_section(title: str, messages: list):
    print(f"\n{'=' * 60}")
    print(f"  {title}  ({len(messages)} Nachrichten)")
    print(f"{'=' * 60}")
    for msg in messages:
        match_label = f"  [{msg['match_type']}]" if "match_type" in msg else ""
        print(f"\n[{msg['date']}] {msg['from']} (ID {msg['id']}){match_label}")
        print(f"  {msg['text']}")


def main():
    parser = argparse.ArgumentParser(description="Extrahiert ListBot- und /-Nachrichten aus einem Telegram-Export")
    parser.add_argument(
        "input",
        nargs="?",
        default=str(_SCRIPT_DIR / "result.json"),
        help="Pfad zur result.json (Standard: result.json im Script-Ordner)",
    )
    parser.add_argument(
        "--bot-name",
        default="ListBot",
        help="Genauer Anzeigename des Bots (Standard: ListBot)",
    )
    parser.add_argument(
        "--output-json",
        metavar="FILE",
        default=str(_SCRIPT_DIR / "ergebnis.json"),
        help="Ergebnis als JSON speichern (Standard: ergebnis.json im Script-Ordner)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Keine Nachrichten auf der Konsole ausgeben",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Fehler: Datei nicht gefunden: {input_path}")
        raise SystemExit(1)

    result = extract_messages(input_path, bot_name=args.bot_name)
    normalized = normalize_prompts(result)

    if not args.quiet:
        lookup = result.get("user_lookup", {})
        print(f"\n{'=' * 60}")
        print(f"  User ID Lookup ({len(lookup)} users)")
        print(f"{'=' * 60}")
        print(f"  {'Display Name':<25} | User ID")
        print(f"  {'-' * 25}-+-{'-' * 15}")
        for name, uid in sorted(lookup.items()):
            print(f"  {name:<25} | {uid}")

        print(f"\n{'=' * 60}")
        print(f"  Chat: {result['chat_name']} (ID {result['chat_id']})")
        print(f"  Prompts (normalisiert): {len(normalized['prompts'])}")
        print(f"{'=' * 60}")
        user_counts = Counter(p["first_name"] for p in normalized["prompts"])
        for name, count in user_counts.most_common():
            print(f"  {name:<20}: {count}")

    out = Path(args.output_json)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    print(f"\n  Gespeichert als: {out}")


if __name__ == "__main__":
    main()
