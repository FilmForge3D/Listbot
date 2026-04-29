#!/usr/bin/env python3
"""Modern Telegram bot for managing writing prompt lists."""

import logging
import os
import sys
from pathlib import Path
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, MessageEntity
from database import init_db, get_list_names, get_prompts, draw_random_prompt, add_prompt, edit_prompt, remove_prompt, get_stats, get_default_list, set_default_list

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


def _render_lists_view(chat_id: int, title: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build the list-selection panel text and keyboard."""
    names = get_list_names(chat_id)
    default = get_default_list(chat_id)
    text = f"*{title}*\n\nYour lists:" if names else f"*{title}*\n\nNo lists yet. Create one!"
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for name in names:
        label = f"⭐ {name}" if name == default else name
        row.append(InlineKeyboardButton(label, callback_data=f"open:{name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    row.append(InlineKeyboardButton("➕ New List", callback_data="new_list"))
    buttons.append(row)
    return text, InlineKeyboardMarkup(buttons)


def _render_list_view(chat_id: int, list_name: str, note: str = "") -> tuple[str, InlineKeyboardMarkup]:
    """Build the detail panel for a single named list."""
    prompts = get_prompts(chat_id, list_name)
    total = len(prompts)
    drawn = sum(1 for p in prompts if p["drawn"])
    header = f"*{list_name}*  ({total} items, {drawn} drawn)"
    text = f"{header}\n\n{note}" if note else header
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Draw", callback_data=f"draw:{list_name}"),
         InlineKeyboardButton("➕ Add", callback_data=f"add:{list_name}")],
        [InlineKeyboardButton("🗑 Remove", callback_data=f"remove:{list_name}"),
         InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{list_name}"),
         InlineKeyboardButton("📋 View", callback_data=f"list:{list_name}:0")],
        [InlineKeyboardButton("📊 Stats", callback_data=f"stats:{list_name}"),
         InlineKeyboardButton("⭐ Default", callback_data=f"set_default:{list_name}")],
        [InlineKeyboardButton("← Back", callback_data="back")],
    ])
    return text, markup


async def _notify(bot, chat_id: int, text: str, thread_id: int | None) -> None:
    """Send an HTML notification to the correct chat thread."""
    await bot.send_message(chat_id, text, parse_mode="HTML", message_thread_id=thread_id)


def _force_reply_msg(user, body: str, bold: str, suffix: str) -> tuple[str, list[MessageEntity]]:
    """Build plain text + entities for a selective ForceReply prompt."""
    name = user.full_name
    prefix = f"{name}, {body}"
    text = f"{prefix}{bold}{suffix}"
    return text, [
        MessageEntity(type=MessageEntity.TEXT_MENTION, offset=0, length=len(name), user=user),
        MessageEntity(type=MessageEntity.BOLD, offset=len(prefix), length=len(bold)),
    ]


_NO_DEFAULT_LIST_MSG = "No default list set. Open /lb, pick a list, and tap ⭐ Default."


async def _send_force_reply(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    thread_id: int | None,
    panel_msg_id: int,
    user,
    action: str,
    body: str,
    bold: str,
    suffix: str,
    list_name: str | None = None,
) -> None:
    """Send a ForceReply prompt and record the pending action in chat_data."""
    msg_text, entities = _force_reply_msg(user, body, bold, suffix)
    prompt_msg = await context.bot.send_message(
        chat_id, msg_text,
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


async def _cleanup_reply_messages(bot, chat_id: int, prompt_msg_id: int, user_msg_id: int) -> None:
    """Delete the ForceReply prompt and the user's reply from chat."""
    await bot.delete_message(chat_id, prompt_msg_id)
    await bot.delete_message(chat_id, user_msg_id)


async def _do_draw(bot, chat_id: int, list_name: str, user_name: str, thread_id: int | None) -> bool:
    """Draw a random undrawn prompt and notify the chat. Returns False if list is empty."""
    prompt = draw_random_prompt(chat_id, list_name)
    if not prompt:
        return False
    added_by = prompt["added_by_name"] or ""
    author_line = f"\n<i>added by <tg-spoiler>{added_by}</tg-spoiler></i>" if added_by else ""
    await _notify(
        bot, chat_id,
        f"🎲 <b>{user_name}</b> drew from <b>{list_name}</b>:\n<blockquote>{prompt['text']}</blockquote>{author_line}",
        thread_id,
    )
    return True


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route inline keyboard button taps."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    chat_title = query.message.chat.title or "Lists"

    if data == "back":
        text, markup = _render_lists_view(chat_id, chat_title)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("open:"):
        list_name = data[5:]
        text, markup = _render_list_view(chat_id, list_name)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("draw:"):
        list_name = data[5:]
        user_name = query.from_user.full_name if query.from_user else "Someone"
        if not await _do_draw(context.bot, chat_id, list_name, user_name, query.message.message_thread_id):
            text, markup = _render_list_view(chat_id, list_name, "⚠️ All items have been drawn.")
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
            return
        await query.message.delete()

    elif data.startswith("list:"):
        parts = data[5:].rsplit(":", 1)
        list_name = parts[0]
        page = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 0
        PAGE_SIZE = 50
        prompts = get_prompts(chat_id, list_name)
        total = len(prompts)
        drawn = sum(1 for p in prompts if p["drawn"])
        start = page * PAGE_SIZE
        page_prompts = prompts[start:start + PAGE_SIZE]
        lines = "\n".join(f"{p['position']}. {p['text']}" for p in page_prompts) or "_Empty_"
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        header = f"*{list_name}*  ({total} items, {drawn} drawn) — page {page + 1}/{total_pages}"
        text = f"{header}\n\n{lines}"
        _, base_markup = _render_list_view(chat_id, list_name)
        if total_pages > 1:
            prev_page = (page - 1) % total_pages
            next_page = (page + 1) % total_pages
            nav_row = [
                InlineKeyboardButton("◀ Prev", callback_data=f"list:{list_name}:{prev_page}"),
                InlineKeyboardButton("Next ▶", callback_data=f"list:{list_name}:{next_page}"),
            ]
            markup = InlineKeyboardMarkup(list(base_markup.inline_keyboard) + [nav_row])
        else:
            markup = base_markup
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("stats:"):
        list_name = data[6:]
        s = get_stats(chat_id, list_name)
        if not s:
            await query.answer("List not found.", show_alert=True)
            return
        user_lines = "\n".join(f"  • {r['name']} — {r['count']}" for r in s["by_user"])
        most = f'_{s["most_drawn"]["text"]}_ ({s["most_drawn"]["count"]}×)' if s["most_drawn"] else "—"
        stats_text = (
            f"*{list_name} — Stats*\n\n"
            f"📝 Prompts: {s['total']}\n"
            f"🎲 Total draws: {s['total_draws']}\n"
            f"😴 Never drawn: {s['never_drawn']}\n"
            f"🏆 Most drawn: {most}\n\n"
            f"👤 Prompts by user:\n{user_lines or '  —'}"
        )
        _, markup = _render_list_view(chat_id, list_name)
        await query.edit_message_text(stats_text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("remove:"):
        list_name = data[7:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "remove", "reply with the position number to remove from ", list_name, ":",
            list_name=list_name,
        )

    elif data.startswith("edit:"):
        list_name = data[5:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "edit", "reply with `position new text` to edit an item in ", list_name, ":",
            list_name=list_name,
        )

    elif data.startswith("add:"):
        list_name = data[4:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "add", "reply with the item to add to ", list_name, ":",
            list_name=list_name,
        )

    elif data.startswith("set_default:"):
        list_name = data[12:]
        set_default_list(chat_id, list_name)
        text, markup = _render_list_view(chat_id, list_name, f"⭐ *{list_name}* is now the default list.")
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data == "new_list":
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "new_list", "reply with the name for the new list", "", ":",
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
        user_name = msg.from_user.full_name if msg.from_user else ""
        position = add_prompt(chat_id, list_name, user_text, added_by_name=user_name)
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await _notify(
            context.bot, chat_id,
            f"✅ <b>{user_name}</b> <i>added #{position} to {list_name}</i>:\n<blockquote>{user_text}</blockquote>",
            msg.message_thread_id,
        )
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "remove":
        list_name = state["list_name"]
        if not user_text.isdigit():
            await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = _render_list_view(chat_id, list_name, "⚠️ Please reply with a position number.")
            await context.bot.edit_message_text(text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown")
            return
        position = int(user_text)
        removed = remove_prompt(chat_id, list_name, position)
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if removed:
            note = f"🗑 Position {position} removed:\n<blockquote>{removed['text']}</blockquote>"
        else:
            note = f"⚠️ No item at position {position}."
        await _notify(context.bot, chat_id, note, msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "edit":
        list_name = state["list_name"]
        parts = user_text.split(None, 1)
        if len(parts) < 2 or not parts[0].isdigit():
            await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = _render_list_view(chat_id, list_name, "⚠️ Format must be: `<position> <new text>`")
            await context.bot.edit_message_text(text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown")
            return
        position, new_text = int(parts[0]), parts[1].strip()
        user_name = msg.from_user.full_name if msg.from_user else ""
        updated = edit_prompt(chat_id, list_name, position, new_text)
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if updated:
            await _notify(
                context.bot, chat_id,
                f"✏️ <b>{user_name}</b> <i>edited #{position} in {list_name}</i>:\n<blockquote>{new_text}</blockquote>",
                msg.message_thread_id,
            )
        else:
            await _notify(context.bot, chat_id, f"⚠️ No item at position {position}.", msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "new_list":
        list_name = user_text
        text, markup = _render_list_view(chat_id, list_name, "✅ List created! Tap ➕ Add to start filling it.")
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown")


async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Draw a random item from the default list."""
    chat_id = update.effective_chat.id
    list_name = get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text(_NO_DEFAULT_LIST_MSG, parse_mode="Markdown")
        return
    user_name = update.message.from_user.full_name if update.message.from_user else "Someone"
    if not await _do_draw(context.bot, chat_id, list_name, user_name, update.message.message_thread_id):
        await update.message.reply_text(f"*{list_name}* is empty.", parse_mode="Markdown")
        return
    await update.message.delete()


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an item to the default list. Usage: /add <item text>"""
    chat_id = update.effective_chat.id
    list_name = get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text(_NO_DEFAULT_LIST_MSG, parse_mode="Markdown")
        return
    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await update.message.reply_text("Usage: `/add <item text>`", parse_mode="Markdown")
        return
    user_name = update.message.from_user.full_name if update.message.from_user else ""
    position = add_prompt(chat_id, list_name, text, added_by_name=user_name)
    await update.message.delete()
    await _notify(
        context.bot, chat_id,
        f"✅ <b>{user_name}</b> <i>added #{position} to {list_name}</i>:\n<blockquote>{text}</blockquote>",
        update.message.message_thread_id,
    )



async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post the interactive list panel in response to /lb."""
    chat = update.effective_chat
    text, markup = _render_lists_view(chat.id, chat.title or "Lists")
    await update.message.delete()
    await context.bot.send_message(
        chat.id, text, reply_markup=markup, parse_mode="Markdown",
        message_thread_id=update.message.message_thread_id,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when /help is issued."""
    help_text = "Use /lb to open the interactive list panel."
    await update.message.reply_text(help_text)


def main() -> None:
    """Start the bot."""
    init_db()
    token = load_token()
    # Create the Application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lb", show_panel))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("draw", draw_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, reply_handler))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
