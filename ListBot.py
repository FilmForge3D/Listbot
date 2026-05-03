#!/usr/bin/env python3
"""Modern Telegram bot for managing writing prompt lists."""

import argparse
import logging
import os
import sys
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TimedOut
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

import db
import i18n as lang

import ui.views as views

from messaging import notify, send_force_reply, cleanup_reply_messages
from actions import do_draw
from text import first_name

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route inline keyboard button taps."""
    query = update.callback_query
    try:
        await query.answer()
    except TimedOut:
        pass
    data = query.data
    chat_id = query.message.chat_id
    chat_title = query.message.chat.title or "Lists"
    if query.message.chat.title:
        db.upsert_user(chat_id, query.message.chat.title)

    if data == "back":
        text, markup = views._render_lists_view(chat_id, chat_title)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("open:"):
        list_name = data[5:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = views._render_list_view(owner_chat_id, list_name)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("draw:"):
        list_name = data[5:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        user_name = query.from_user.full_name if query.from_user else "Someone"
        if not await do_draw(
            context.bot, owner_chat_id, list_name, user_name, query.message.message_thread_id, notify_chat_id=chat_id
        ):
            text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("err_all_drawn"))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
            return
        await query.message.delete()

    elif data.startswith("list:"):
        parts = data[5:].rsplit(":", 1)
        list_name = parts[0]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        page = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 0
        PAGE_SIZE = 50
        prompts = db.get_prompts(owner_chat_id, list_name)
        total = len(prompts)
        drawn = sum(1 for p in prompts if p["drawn"])
        start = page * PAGE_SIZE
        page_prompts = prompts[start:start + PAGE_SIZE]
        lines = "\n".join(f"{p['position']}. {p['text']}" for p in page_prompts) or lang.t("panel_empty")
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        paged = lang.t("panel_list_header_paged", total=total, drawn=drawn, page=page + 1, total_pages=total_pages)
        header = f"*{list_name}*  {paged}"
        text = f"{header}\n\n{lines}"
        _, base_markup = views._render_list_view(owner_chat_id, list_name)
        if total_pages > 1:
            prev_page = (page - 1) % total_pages
            next_page = (page + 1) % total_pages
            nav_row = [
                InlineKeyboardButton(lang.t("btn_prev"), callback_data=f"list:{list_name}:{prev_page}"),
                InlineKeyboardButton(lang.t("btn_next"), callback_data=f"list:{list_name}:{next_page}"),
            ]
            markup = InlineKeyboardMarkup(list(base_markup.inline_keyboard) + [nav_row])
        else:
            markup = base_markup
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("stats:"):
        list_name = data[6:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        s = db.get_stats(owner_chat_id, list_name)
        if not s:
            await query.answer(lang.t("err_list_not_found"), show_alert=True)
            return
        user_lines = "\n".join(
            lang.t("stats_user_line", name=first_name(r["name"]), count=r["count"]) for r in s["by_user"]
        )
        most = (
            lang.t("stats_most_drawn_fmt", text=s["most_drawn"]["text"], count=s["most_drawn"]["count"])
            if s["most_drawn"]
            else lang.t("stats_most_drawn_none")
        )
        stats_text = (
            f"*{lang.t('stats_title', list_name=list_name)}*\n\n"
            f"{lang.t('stats_prompts', total=s['total'])}\n"
            f"{lang.t('stats_draws', total_draws=s['total_draws'])}\n"
            f"{lang.t('stats_never_drawn', never_drawn=s['never_drawn'])}\n"
            f"{lang.t('stats_most_drawn', most=most)}\n\n"
            f"{lang.t('stats_by_user')}\n{user_lines or lang.t('stats_no_users')}"
        )
        _, markup = views._render_list_view(owner_chat_id, list_name)
        await query.edit_message_text(stats_text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("remove:"):
        list_name = data[7:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        if not db.get_prompts(owner_chat_id, list_name):
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(lang.t("btn_db.delete_list"), callback_data=f"db.delete_list_confirm:{list_name}"),
                InlineKeyboardButton(lang.t("btn_back_cancel"), callback_data=f"open:{list_name}"),
            ]])
            await query.edit_message_text(
                lang.t("confirm_delete_prompt", list_name=list_name), reply_markup=markup, parse_mode="Markdown"
            )
            return
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "remove", lang.t("fr_remove_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("edit:"):
        list_name = data[5:]
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "edit", lang.t("fr_edit_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("add:"):
        list_name = data[4:]
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "add", lang.t("fr_add_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("set_default:"):
        list_name = data[12:]
        db.set_default_list(chat_id, list_name)
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("confirm_set_default", list_name=list_name))
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("db.delete_list_confirm:"):
        list_name = data[20:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        if db.delete_list(owner_chat_id, list_name):
            text, markup = views._render_lists_view(chat_id, lang.t("confirm_list_deleted", list_name=list_name))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        else:
            text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("err_cannot_delete"))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("share:"):
        list_name = data[6:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("share_invite:"):
        list_name = data[13:]
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "share_invite", lang.t("fr_invite_body", chat_id=chat_id, list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("share_remove:"):
        list_name = data[13:]
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "share_remove", lang.t("fr_remove_guest_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("share_transfer:"):
        list_name = data[15:]
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "share_transfer", lang.t("fr_transfer_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("share_leave:"):
        list_name = data[12:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name)
        if owner_chat_id:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
                    (owner_chat_id, list_name),
                ).fetchone()
            if row:
                db.remove_list_share(row["id"], chat_id)
        text, markup = views._render_lists_view(chat_id, query.message.chat.title or "Lists")
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data == "new_list":
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "new_list", lang.t("fr_new_list_body"),
        )


async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ForceReply responses for add and new_list actions."""
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

    if state["action"] == "add":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        user_name = msg.from_user.full_name if msg.from_user else ""
        db.upsert_user(msg.from_user.id, user_name)
        position = db.add_prompt(owner_chat_id, list_name, user_text, added_by_id=msg.from_user.id)
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await notify(
            context.bot, chat_id,
            lang.t("notify_added", user=first_name(user_name), position=position, list_name=list_name, text=user_text),
            msg.message_thread_id,
        )
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "remove":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        if not user_text.isdigit():
            await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("err_not_a_number"))
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        position = int(user_text)
        removed = db.remove_prompt(owner_chat_id, list_name, position)
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        note = (
            lang.t("notify_removed", position=position, text=removed["text"])
            if removed
            else lang.t("err_no_item_at", position=position)
        )
        await notify(context.bot, chat_id, note, msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "edit":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        parts = user_text.split(None, 1)
        if parts[0].lower() == "rename":
            new_name = parts[1].strip() if len(parts) > 1 else ""
            await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            if not new_name:
                text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("err_rename_format"))
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
                return
            renamed = db.rename_list(owner_chat_id, list_name, new_name)
            if renamed:
                await notify(
                    context.bot, chat_id,
                    lang.t("notify_renamed", old_name=list_name, new_name=new_name),
                    msg.message_thread_id,
                )
                text, markup = views._render_list_view(owner_chat_id, new_name)
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
            else:
                text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("err_rename_exists", name=new_name))
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
            return
        if len(parts) < 2 or not parts[0].isdigit():
            await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = views._render_list_view(owner_chat_id, list_name, lang.t("err_edit_format"))
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        position, new_text = int(parts[0]), parts[1].strip()
        user_name = msg.from_user.full_name if msg.from_user else ""
        updated = db.edit_prompt(owner_chat_id, list_name, position, new_text)
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if updated:
            await notify(
                context.bot, chat_id,
                lang.t("notify_edited", user=first_name(user_name), position=position, list_name=list_name, text=new_text),
                msg.message_thread_id,
            )
        else:
            await notify(context.bot, chat_id, lang.t("err_no_item_at", position=position), msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "new_list":
        list_name = user_text
        text, markup = views._render_list_view(chat_id, list_name, lang.t("confirm_list_created"))
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await context.bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_invite":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        guest_id = int(user_text)
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lists WHERE chat_id=? AND list_name=?", (owner_chat_id, list_name)
            ).fetchone()
        if row and db.add_list_share(row["id"], guest_id):
            note = lang.t("confirm_invite_ok", chat_id=guest_id, list_name=list_name)
        else:
            note = lang.t("err_invite_failed", chat_id=guest_id)
        text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_remove":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        guest_id = int(user_text)
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lists WHERE chat_id=? AND list_name=?", (owner_chat_id, list_name)
            ).fetchone()
        if row and db.remove_list_share(row["id"], guest_id):
            note = lang.t("confirm_remove_guest_ok", chat_id=guest_id, list_name=list_name)
        else:
            note = lang.t("err_remove_guest_failed", chat_id=guest_id)
        text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_transfer":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        new_owner_id = int(user_text)
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lists WHERE chat_id=? AND list_name=?", (owner_chat_id, list_name)
            ).fetchone()
        if row and db.transfer_list_ownership(row["id"], new_owner_id):
            note = lang.t("confirm_transfer_ok", list_name=list_name, new_owner=new_owner_id)
            text, markup = views._render_share_panel(chat_id, list_name, new_owner_id)
        else:
            note = lang.t("err_transfer_failed", chat_id=new_owner_id)
            text, markup = views._render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
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
            text, markup = views._render_list_view(owner_chat_id, list_name)
        else:
            chat_title = msg.chat.title or "Lists"
            text, markup = views._render_lists_view(chat_id, chat_title)
        try:
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id,
                reply_markup=markup, parse_mode="Markdown",
            )
        except Exception:
            pass


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
        context.bot, chat_id,
        lang.t("notify_added", user=first_name(user_name), position=position, list_name=list_name, text=text),
        update.message.message_thread_id,
    )



async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post the interactive list panel in response to /lb."""
    chat = update.effective_chat
    text, markup = views._render_lists_view(chat.id, chat.title or "Lists")
    await update.message.delete()
    await context.bot.send_message(
        chat.id, text, reply_markup=markup, parse_mode="Markdown",
        message_thread_id=update.message.message_thread_id,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when /help is issued."""
    chat = update.effective_chat
    await update.message.delete()
    await context.bot.send_message(
        chat.id, lang.t("help_text", chat_id=chat.id), parse_mode="HTML",
        message_thread_id=update.message.message_thread_id,
    )


def main() -> None:
    """Start the bot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="", help="Locale to use (default: BOT_LANG env var or 'en')")
    args = parser.parse_args()
    lang.load_locale(args.lang)
    db.init_db()
    token = load_token()
    # Create the Application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lb", show_panel))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("draw", draw_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, reply_handler))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
