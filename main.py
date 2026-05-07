#!/usr/bin/env python3
"""Modern Telegram bot for managing writing prompt lists."""

import argparse
import logging

from telegram import Update
from telegram.ext import Application

import db
import handlers
import i18n as lang
from config import load_token

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="", help="Locale to use (default: BOT_LANG env var or 'en')")
    args = parser.parse_args()
    lang.load_locale(args.lang)
    db.init_db()
    token = load_token()
    application = Application.builder().token(token).build()
    handlers.register_handlers(application)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
