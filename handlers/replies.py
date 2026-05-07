from telegram import Bot, Message, Update
from telegram.ext import ContextTypes

import db
import i18n as lang
from messaging import cleanup_reply_messages, notify
from text import first_name
from ui import views


async def _handle_add(
    bot: Bot,
    msg: Message,
    state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Add a new prompt to the list."""
    list_name = state["list_name"]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    user_name = msg.from_user.full_name if msg.from_user else ""
    db.upsert_user(msg.from_user.id, user_name)
    position = db.add_prompt(owner_chat_id, list_name, user_text, added_by_id=msg.from_user.id)
    await cleanup_reply_messages(bot, chat_id, prompt_msg_id, msg.message_id)
    await notify(
        bot,
        chat_id,
        lang.t("notify_added", user=first_name(user_name), position=position, list_name=list_name, text=user_text),
        msg.message_thread_id,
    )
    await bot.delete_message(chat_id, panel_msg_id)


async def _handle_remove(
    bot: Bot,
    msg: Message,
    state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Remove a prompt at the given position."""
    list_name = state["list_name"]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    await cleanup_reply_messages(bot, chat_id, prompt_msg_id, msg.message_id)
    if not user_text.isdigit():
        text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_not_a_number"))
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )
        return
    position = int(user_text)
    removed = db.remove_prompt(owner_chat_id, list_name, position)
    note = (
        lang.t("notify_removed", position=position, text=removed["text"])
        if removed
        else lang.t("err_no_item_at", position=position)
    )
    await notify(bot, chat_id, note, msg.message_thread_id)
    await bot.delete_message(chat_id, panel_msg_id)


async def _handle_new_list(
    bot: Bot,
    msg: Message,
    _state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Create a new list with the given name."""
    list_name = user_text
    text, markup = views.render_list_view(chat_id, list_name, lang.t("confirm_list_created"))
    await cleanup_reply_messages(bot, chat_id, prompt_msg_id, msg.message_id)
    await bot.edit_message_text(
        text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
    )


async def _handle_rename(
    bot: Bot,
    msg: Message,
    list_name: str,
    owner_chat_id: int,
    user_text: str,
    panel_msg_id: int,
    chat_id: int,
) -> None:
    """Rename the list to the name given after the 'rename' keyword."""
    parts = user_text.split(None, 1)
    new_name = parts[1].strip() if len(parts) > 1 else ""
    if not new_name:
        text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_rename_format"))
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )
        return
    renamed = db.rename_list(owner_chat_id, list_name, new_name)
    if renamed:
        await notify(
            bot,
            chat_id,
            lang.t("notify_renamed", old_name=list_name, new_name=new_name),
            msg.message_thread_id,
        )
        text, markup = views.render_list_view(owner_chat_id, new_name)
    else:
        text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_rename_exists", name=new_name))
    await bot.edit_message_text(
        text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
    )


async def _handle_edit(
    bot: Bot,
    msg: Message,
    state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Edit a prompt at the given position, or rename the list."""
    list_name = state["list_name"]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    parts = user_text.split(None, 1)
    await cleanup_reply_messages(bot, chat_id, prompt_msg_id, msg.message_id)
    if parts[0].lower() == "rename":
        await _handle_rename(bot, msg, list_name, owner_chat_id, user_text, panel_msg_id, chat_id)
        return
    if len(parts) < 2 or not parts[0].isdigit():
        text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_edit_format"))
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )
        return
    position, new_text = int(parts[0]), parts[1].strip()
    user_name = msg.from_user.full_name if msg.from_user else ""
    updated = db.edit_prompt(owner_chat_id, list_name, position, new_text)
    if updated:
        await notify(
            bot,
            chat_id,
            lang.t("notify_edited", user=first_name(user_name), position=position, list_name=list_name, text=new_text),
            msg.message_thread_id,
        )
    else:
        await notify(bot, chat_id, lang.t("err_no_item_at", position=position), msg.message_thread_id)
    await bot.delete_message(chat_id, panel_msg_id)


async def _resolve_share_id(
    bot: Bot,
    msg: Message,
    chat_id: int,
    list_name: str,
    owner_chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> int | None:
    """Clean up reply, validate that user_text is a chat ID; show the share panel and return None if not."""
    await cleanup_reply_messages(bot, chat_id, prompt_msg_id, msg.message_id)
    if not user_text.lstrip("-").isdigit():
        text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )
        return None
    return int(user_text)


async def _handle_share_invite(
    bot: Bot,
    msg: Message,
    state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Add a new share recipient by chat ID."""
    list_name = state["list_name"]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    guest_id = await _resolve_share_id(bot, msg, chat_id, list_name, owner_chat_id, user_text, panel_msg_id, prompt_msg_id)
    if guest_id is None:
        return
    list_id = db.get_list_id(owner_chat_id, list_name)
    if list_id and db.add_list_share(list_id, guest_id):
        note = lang.t("confirm_invite_ok", chat_id=guest_id, list_name=list_name)
    else:
        note = lang.t("err_invite_failed", chat_id=guest_id)
    text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
    await bot.edit_message_text(
        f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
    )


async def _handle_share_remove(
    bot: Bot,
    msg: Message,
    state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Remove a share recipient by chat ID."""
    list_name = state["list_name"]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    guest_id = await _resolve_share_id(bot, msg, chat_id, list_name, owner_chat_id, user_text, panel_msg_id, prompt_msg_id)
    if guest_id is None:
        return
    list_id = db.get_list_id(owner_chat_id, list_name)
    if list_id and db.remove_list_share(list_id, guest_id):
        note = lang.t("confirm_remove_guest_ok", chat_id=guest_id, list_name=list_name)
    else:
        note = lang.t("err_remove_guest_failed", chat_id=guest_id)
    text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
    await bot.edit_message_text(
        f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
    )


async def _handle_share_transfer(
    bot: Bot,
    msg: Message,
    state: dict[str, str | int],
    chat_id: int,
    user_text: str,
    panel_msg_id: int,
    prompt_msg_id: int,
) -> None:
    """Transfer list ownership to another chat."""
    list_name = state["list_name"]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    new_owner_id = await _resolve_share_id(bot, msg, chat_id, list_name, owner_chat_id, user_text, panel_msg_id, prompt_msg_id)
    if new_owner_id is None:
        return
    list_id = db.get_list_id(owner_chat_id, list_name)
    if list_id and db.transfer_list_ownership(list_id, new_owner_id):
        note = lang.t("confirm_transfer_ok", list_name=list_name, new_owner=new_owner_id)
        text, markup = views.render_share_panel(chat_id, list_name, new_owner_id)
    else:
        note = lang.t("err_transfer_failed", chat_id=new_owner_id)
        text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
    await bot.edit_message_text(
        f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
    )


_HANDLERS = {
    "add": _handle_add,
    "remove": _handle_remove,
    "new_list": _handle_new_list,
    "edit": _handle_edit,
    "share_invite": _handle_share_invite,
    "share_remove": _handle_share_remove,
    "share_transfer": _handle_share_transfer,
}


async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch ForceReply responses to the appropriate action handler."""
    msg = update.message
    if not msg.from_user:
        return
    state = context.chat_data.pop(f"user:{msg.from_user.id}", None)
    if not state:
        return

    chat_id = msg.chat_id
    user_text = msg.text.strip()
    panel_msg_id = state["panel_msg_id"]
    prompt_msg_id = state["prompt_msg_id"]

    handler = _HANDLERS.get(state["action"])
    if handler:
        await handler(context.bot, msg, state, chat_id, user_text, panel_msg_id, prompt_msg_id)
