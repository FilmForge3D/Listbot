import json
import os
import sys
from pathlib import Path

_T: dict[str, str] = {}


def load_locale(lang: str = "") -> None:
    global _T
    lang = (lang or os.environ.get("BOT_LANG", "en")).strip()
    path = Path(__file__).parent / "locales" / f"{lang}.json"
    if not path.exists():
        print(f"[strings] Locale '{lang}' not found, falling back to 'en'", file=sys.stderr)
        path = Path(__file__).parent / "locales" / "en.json"
    _T = json.loads(path.read_text(encoding="utf-8"))


def t(key: str, **kwargs: object) -> str:
    s = _T.get(key, key)
    return s.format(**kwargs) if kwargs else s
