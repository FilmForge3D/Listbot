#!/usr/bin/env python3
"""Modern Telegram bot for managing writing prompt lists."""

import logging
import sys
from pathlib import Path
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from database import init_db, get_list_names, get_prompts, draw_random_prompt, add_prompt, get_stats, get_default_list, set_default_list

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_token() -> str:
    """Load bot token from token.txt file."""
    token_path = Path("token.txt")
    if not token_path.exists():
        logger.error("token.txt not found. Please create it based on example.token.txt")
        sys.exit(1)

    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        logger.error("token.txt is empty")
        sys.exit(1)

    return token


def _render_lists_view(chat_id: int, title: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build the list-selection panel text and keyboard."""
    names = get_list_names(chat_id)
    text = f"*{title}*\n\nYour lists:" if names else f"*{title}*\n\nNo lists yet. Create one!"
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for name in names:
        row.append(InlineKeyboardButton(name, callback_data=f"open:{name}"))
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
         InlineKeyboardButton("📋 View", callback_data=f"list:{list_name}:0")],
        [InlineKeyboardButton("📊 Stats", callback_data=f"stats:{list_name}"),
         InlineKeyboardButton("⭐ Default", callback_data=f"set_default:{list_name}")],
        [InlineKeyboardButton("← Back", callback_data="back")],
    ])
    return text, markup


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
        prompt = draw_random_prompt(chat_id, list_name)
        if prompt:
            note = f"🎲 Drew: _{prompt['text']}_"
            await query.message.reply_text(
                f"🎲 *{user_name}* drew from *{list_name}*:\n_{prompt['text']}_",
                parse_mode="Markdown",
            )
        else:
            note = "⚠️ All items have been drawn."
        text, markup = _render_list_view(chat_id, list_name, note)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

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
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀ Prev", callback_data=f"list:{list_name}:{page - 1}"))
        if start + PAGE_SIZE < total:
            nav_row.append(InlineKeyboardButton("Next ▶", callback_data=f"list:{list_name}:{page + 1}"))
        markup = InlineKeyboardMarkup(list(base_markup.inline_keyboard) + [nav_row]) if nav_row else base_markup
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

    elif data.startswith("add:"):
        list_name = data[4:]
        prompt_msg = await query.message.reply_text(
            f"Reply with the item to add to *{list_name}*:",
            reply_markup=ForceReply(selective=True),
            parse_mode="Markdown",
        )
        context.chat_data[prompt_msg.message_id] = {
            "action": "add",
            "list_name": list_name,
            "panel_msg_id": query.message.message_id,
        }

    elif data.startswith("set_default:"):
        list_name = data[12:]
        set_default_list(chat_id, list_name)
        text, markup = _render_list_view(chat_id, list_name, f"⭐ *{list_name}* is now the default list.")
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data == "new_list":
        prompt_msg = await query.message.reply_text(
            "Reply with the name for the new list:",
            reply_markup=ForceReply(selective=True),
        )
        context.chat_data[prompt_msg.message_id] = {
            "action": "new_list",
            "panel_msg_id": query.message.message_id,
        }


async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ForceReply responses for add and new_list actions."""
    msg = update.message
    if not msg.reply_to_message:
        return
    state = context.chat_data.pop(msg.reply_to_message.message_id, None)
    if not state:
        return

    chat_id = msg.chat_id
    user_text = msg.text.strip()
    panel_msg_id = state["panel_msg_id"]

    if state["action"] == "add":
        list_name = state["list_name"]
        user_name = msg.from_user.full_name if msg.from_user else ""
        add_prompt(chat_id, list_name, user_text, added_by_name=user_name)
        await context.bot.delete_message(chat_id, msg.reply_to_message.message_id)
        await context.bot.delete_message(chat_id, msg.message_id)
        await context.bot.send_message(
            chat_id,
            f"✅ *{user_name}* added to *{list_name}*:\n_{user_text}_",
            parse_mode="Markdown",
        )
        text, markup = _render_list_view(chat_id, list_name)
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown")

    elif state["action"] == "new_list":
        list_name = user_text
        text, markup = _render_list_view(chat_id, list_name, "✅ List created! Tap ➕ Add to start filling it.")
        await context.bot.delete_message(chat_id, msg.reply_to_message.message_id)
        await context.bot.delete_message(chat_id, msg.message_id)
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown")


async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Draw a random item from the default list."""
    chat_id = update.effective_chat.id
    list_name = get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text("No default list set. Open /lb, pick a list, and tap ⭐ Default.", parse_mode="Markdown")
        return
    user_name = update.message.from_user.full_name if update.message.from_user else "Someone"
    prompt = draw_random_prompt(chat_id, list_name)
    if not prompt:
        await update.message.reply_text(f"*{list_name}* is empty.", parse_mode="Markdown")
        return
    await update.message.delete()
    await context.bot.send_message(
        chat_id, f"🎲 *{user_name}* drew from *{list_name}*:\n_{prompt['text']}_", parse_mode="Markdown"
    )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an item to the default list. Usage: /add <item text>"""
    chat_id = update.effective_chat.id
    list_name = get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text("No default list set. Open /lb, pick a list, and tap ⭐ Default.", parse_mode="Markdown")
        return
    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await update.message.reply_text("Usage: `/add <item text>`", parse_mode="Markdown")
        return
    user_name = update.message.from_user.full_name if update.message.from_user else ""
    add_prompt(chat_id, list_name, text, added_by_name=user_name)
    await update.message.delete()
    await context.bot.send_message(
        chat_id, f"✅ *{user_name}* added to *{list_name}*:\n_{text}_", parse_mode="Markdown"
    )



async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post the interactive list panel in response to /lb."""
    chat = update.effective_chat
    text, markup = _render_lists_view(chat.id, chat.title or "Lists")
    await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


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
