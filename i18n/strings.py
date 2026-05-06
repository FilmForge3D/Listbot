import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_T: dict[str, str] = {}


def load_locale(lang: str = "") -> None:
    """Load locale strings from a JSON file; falls back to 'en' if the requested locale is missing."""
    global _T
    lang = (lang or os.environ.get("BOT_LANG", "en")).strip()
    path = Path(__file__).parent / "locales" / f"{lang}.json"
    if not path.exists():
        logger.warning("Locale '%s' not found, falling back to 'en'", lang)
        path = Path(__file__).parent / "locales" / "en.json"
    _T = json.loads(path.read_text(encoding="utf-8"))


def t(key: str, **kwargs: object) -> str:
    s = _T.get(key, key)
    return s.format(**kwargs) if kwargs else s
