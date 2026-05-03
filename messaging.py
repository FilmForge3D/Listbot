from telegram import ForceReply, MessageEntity
from telegram.ext import ContextTypes

import i18n as lang


async def notify(bot, chat_id: int, text: str, thread_id: int | None) -> None:
    """Send an HTML notification to the correct chat thread."""
    await bot.send_message(chat_id, text, parse_mode="HTML", message_thread_id=thread_id)


def force_reply_msg(user, body: str, bold_text: str) -> tuple[str, list[MessageEntity]]:
    """Build plain text + entities for a selective ForceReply prompt."""
    name = user.full_name
    text = f"{name}, {body}"
    entities: list[MessageEntity] = [
        MessageEntity(type=MessageEntity.TEXT_MENTION, offset=0, length=len(name), user=user),
    ]
    if bold_text:
        offset = text.find(bold_text)
        if offset >= 0:
            entities.append(MessageEntity(type=MessageEntity.BOLD, offset=offset, length=len(bold_text)))
    return text, entities


async def send_force_reply(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    thread_id: int | None,
    panel_msg_id: int,
    user,
    action: str,
    body: str,
    bold_text: str = "",
    list_name: str | None = None,
) -> None:
    """Send a ForceReply prompt and record the pending action in chat_data."""
    msg_text, entities = force_reply_msg(user, body, bold_text)
    prompt_msg = await context.bot.send_message(
        chat_id, msg_text + "\n" + lang.t("cancel_hint"),
        reply_markup=ForceReply(selective=True),
        entities=entities,
        message_thread_id=thread_id,
    )
    state: dict = {
        "action": action,
        "panel_msg_id": panel_msg_id,
        "prompt_msg_id": prompt_msg.message_id,
    }
    if list_name is not None:
        state["list_name"] = list_name
    context.chat_data[f"user:{user.id}"] = state


async def cleanup_reply_messages(bot, chat_id: int, prompt_msg_id: int, user_msg_id: int) -> None:
    """Delete the ForceReply prompt and the user's reply from chat."""
    await bot.delete_message(chat_id, prompt_msg_id)
    await bot.delete_message(chat_id, user_msg_id)