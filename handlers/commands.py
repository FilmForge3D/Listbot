from telegram import Update
from telegram.ext import ContextTypes

import db
import i18n as lang
from actions import do_draw
from messaging import notify
from text import first_name
from ui import views


async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Draw a random item from the default list."""
    chat_id = update.effective_chat.id
    list_name = db.get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text(lang.t("err_no_default"), parse_mode="Markdown")
        return
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    user_name = update.message.from_user.full_name if update.message.from_user else "Someone"
    if not await do_draw(
        context.bot, owner_chat_id, list_name, user_name, update.message.message_thread_id, notify_chat_id=chat_id
    ):
        await update.message.reply_text(lang.t("err_list_empty", list_name=list_name), parse_mode="Markdown")
        return
    await update.message.delete()


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an item to the default list. Usage: /add <item text>"""
    chat_id = update.effective_chat.id
    list_name = db.get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text(lang.t("err_no_default"), parse_mode="Markdown")
        return
    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await update.message.reply_text(lang.t("err_add_usage"), parse_mode="Markdown")
        return
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    user_name = update.message.from_user.full_name if update.message.from_user else ""
    db.upsert_user(update.message.from_user.id, user_name)
    position = db.add_prompt(owner_chat_id, list_name, text, added_by_id=update.message.from_user.id)
    await update.message.delete()
    await notify(
        context.bot,
        chat_id,
        lang.t("notify_added", user=first_name(user_name), position=position, list_name=list_name, text=text),
        update.message.message_thread_id,
    )


async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post the interactive list panel in response to /lb."""
    chat = update.effective_chat
    text, markup = views.render_lists_view(chat.id, chat.title or "Lists")
    await update.message.delete()
    await context.bot.send_message(
        chat.id,
        text,
        reply_markup=markup,
        parse_mode="Markdown",
        message_thread_id=update.message.message_thread_id,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when /help is issued."""
    chat = update.effective_chat
    await update.message.delete()
    await context.bot.send_message(
        chat.id,
        lang.t("help_text", chat_id=chat.id),
        parse_mode="HTML",
        message_thread_id=update.message.message_thread_id,
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel a pending ForceReply action for the invoking user."""
    msg = update.message
    if not msg or not msg.from_user:
        return
    state = context.chat_data.pop(f"user:{msg.from_user.id}", None)
    await msg.delete()
    if not state:
        return
    chat_id = msg.chat_id
    try:
        await context.bot.delete_message(chat_id, state["prompt_msg_id"])
    except Exception:
        pass
    list_name = state.get("list_name")
    panel_msg_id = state.get("panel_msg_id")
    if panel_msg_id:
        if list_name:
            owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
            text, markup = views.render_list_view(owner_chat_id, list_name)
        else:
            chat_title = msg.chat.title or "Lists"
            text, markup = views.render_lists_view(chat_id, chat_title)
        try:
            await context.bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=panel_msg_id,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        except Exception:
            pass
