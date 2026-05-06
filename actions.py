from telegram import Bot

import db
import i18n as lang
from messaging import notify
from text import first_name


async def do_draw(
    bot: Bot, chat_id: int, list_name: str, user_name: str, thread_id: int | None, notify_chat_id: int | None = None
) -> bool:
    """Draw a random prompt and notify. chat_id is the list owner; notify_chat_id is where to send the result."""
    prompt = db.draw_random_prompt(chat_id, list_name)
    if not prompt:
        return False
    added_by = first_name(prompt["added_by_name"]) if prompt["added_by_name"] else ""
    author_line = lang.t("notify_drew_author", added_by=added_by) if added_by else ""
    msg = lang.t(
        "notify_drew", user=first_name(user_name), list_name=list_name, text=prompt["text"], author_line=author_line
    )
    await notify(bot, notify_chat_id if notify_chat_id is not None else chat_id, msg, thread_id)
    return True
