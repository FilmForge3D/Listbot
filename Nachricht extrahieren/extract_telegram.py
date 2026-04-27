#!/usr/bin/env python3
"""
Extrahiert aus einem Telegram-Gruppenexport (result.json):
  1. Relevante Nachrichten von ListBot (drew/added the following, hat X gegruppt)
  2. Nachrichten die mit / beginnen
"""

import json
import re
import argparse
from difflib import get_close_matches
from pathlib import Path


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
        return "".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in content
        )
    return content


def load_json_tolerant(path: Path) -> dict:
    """Lädt JSON – bei Fehler wird json_repair als Fallback versucht."""
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Warnung: JSON-Fehler ({e}), versuche automatische Reparatur …")
        try:
            from json_repair import repair_json
            data = json.loads(repair_json(raw))
            print("Reparatur erfolgreich.")
            return data
        except ImportError:
            print(
                "Tipp: Installiere json_repair für automatische Reparatur:\n"
                "  pip install json-repair\n"
            )
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

        if text.startswith("/"):
            slash_msgs.append(entry)

    # Deduplizierung: ListBot added/gruppt/edited-Nachrichten entfernen,
    # wenn ein /add- oder /edit-Befehl in einem Fenster von MSG_WINDOW IDs davor liegt
    MSG_WINDOW = 5
    OVERLAP_TYPES = {"added", "gruppt", "edited"}
    slash_ids = {msg["id"] for msg in slash_msgs if _is_add_edit_cmd(msg["text"])}
    listbot_msgs = [
        msg for msg in listbot_msgs
        if msg["match_type"] not in OVERLAP_TYPES
        or not any((msg["id"] - w) in slash_ids for w in range(1, MSG_WINDOW + 1))
    ]

    # Deduplizierung: added/gruppt entfernen wenn ein späteres edit dieselbe Position betrifft;
    # bei mehreren edits nur den letzten behalten
    edited_positions = {
        _extract_position(msg["text"])
        for msg in listbot_msgs if msg["match_type"] == "edited"
    } - {None}
    seen_edited: set[int] = set()
    merged: list[dict] = []
    for msg in reversed(listbot_msgs):
        pos = _extract_position(msg["text"])
        if msg["match_type"] == "edited":
            if pos in seen_edited:
                continue
            seen_edited.add(pos)
        elif msg["match_type"] in {"added", "gruppt"} and pos in edited_positions:
            continue
        merged.append(msg)
    listbot_msgs = list(reversed(merged))

    chat_id = data.get("id")
    chat_name = data.get("name", "")
    return {"chat_id": chat_id, "chat_name": chat_name, "listbot": listbot_msgs, "slash_commands": slash_msgs}


def print_section(title: str, messages: list):
    print(f"\n{'='*60}")
    print(f"  {title}  ({len(messages)} Nachrichten)")
    print(f"{'='*60}")
    for msg in messages:
        match_label = f"  [{msg['match_type']}]" if "match_type" in msg else ""
        print(f"\n[{msg['date']}] {msg['from']} (ID {msg['id']}){match_label}")
        print(f"  {msg['text']}")


def main():
    parser = argparse.ArgumentParser(
        description="Extrahiert ListBot- und /-Nachrichten aus einem Telegram-Export"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="result.json",
        help="Pfad zur result.json (Standard: result.json)",
    )
    parser.add_argument(
        "--bot-name",
        default="ListBot",
        help="Genauer Anzeigename des Bots (Standard: ListBot)",
    )
    parser.add_argument(
        "--output-json",
        metavar="FILE",
        help="Ergebnis zusätzlich als JSON speichern",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Keine Nachrichten auf der Konsole ausgeben",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Fehler: Datei nicht gefunden: {input_path}")
        raise SystemExit(1)

    result = extract_messages(input_path, bot_name=args.bot_name)

    if not args.quiet:
        print_section(f"Nachrichten von {args.bot_name}", result["listbot"])
        print_section("Nachrichten die mit / beginnen", result["slash_commands"])

    print(f"\n{'='*60}")
    print(f"  Zusammenfassung")
    print(f"{'='*60}")
    print(f"  Chat                       : {result['chat_name']} (ID {result['chat_id']})")
    print(f"  {args.bot_name}-Nachrichten : {len(result['listbot'])}")
    print(f"  /-Nachrichten              : {len(result['slash_commands'])}")

    if args.output_json:
        out = Path(args.output_json)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n  Gespeichert als: {out}")


if __name__ == "__main__":
    main()