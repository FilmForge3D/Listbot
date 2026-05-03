import re

def first_name(name: str) -> str:
    """Return the part of a name before the first whitespace, symbol, or punctuation."""
    m = re.match(r"[^\s\W]+", name, re.UNICODE)
    return m.group(0) if m else name