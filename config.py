import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "."))


def load_token() -> str:
    """Load bot token from BOT_TOKEN env var or token.txt file."""
    token = os.environ.get("BOT_TOKEN", "").strip()
    if token:
        return token

    token_path = Path("token.txt")
    if not token_path.exists():
        logger.error("token.txt not found and BOT_TOKEN env var not set")
        sys.exit(1)

    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        logger.error("token.txt is empty")
        sys.exit(1)

    return token
