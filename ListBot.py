#!/usr/bin/env python3
"""Modern Telegram bot for managing writing prompt lists."""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Update
from telegram.error import TimedOut
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from database import (
    add_list_share,
    add_prompt,
    delete_list,
    draw_random_prompt,
    edit_prompt,
    get_default_list,
    get_list_names,
    get_list_shares,
    get_prompts,
    get_recently_drawn_prompts,
    get_shared_lists,
    get_stats,
    init_db,
    lookup_name,
    remove_list_share,
    remove_prompt,
    rename_list,
    resolve_list_owner,
    set_default_list,
    transfer_list_ownership,
    upsert_user,
)
import i18n as lang

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
    owned = get_list_names(chat_id)
    shared = get_shared_lists(chat_id)
    default = get_default_list(chat_id)
    has_any = bool(owned or shared)
    text = f"*{title}*\n\n{lang.t('panel_your_lists')}" if has_any else f"*{title}*\n\n{lang.t('panel_no_lists')}"
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for name in owned:
        label = f"⭐ {name}" if name == default else name
        row.append(InlineKeyboardButton(label, callback_data=f"open:{name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    for s in shared:
        name = s["list_name"]
        label = f"⭐ 🔗 {name}" if name == default else f"🔗 {name}"
        row.append(InlineKeyboardButton(label, callback_data=f"open:{name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(lang.t("btn_new_list"), callback_data="new_list")])
    return text, InlineKeyboardMarkup(buttons)


def _render_list_view(chat_id: int, list_name: str, note: str = "") -> tuple[str, InlineKeyboardMarkup]:
    """Build the detail panel for a single named list."""
    prompts = get_prompts(chat_id, list_name)
    total = len(prompts)
    drawn = sum(1 for p in prompts if p["drawn"])
    header = f"*{list_name}*  {lang.t('panel_list_header', total=total, drawn=drawn)}"
    recent = get_recently_drawn_prompts(chat_id, list_name)
    if recent:
        lines = "\n".join(f"• {p['text']}" for p in recent)
        recent_section = f"\n\n*{lang.t('panel_recent_header')}*\n{lines}"
    else:
        recent_section = ""
    text = f"{header}{recent_section}\n\n{note}" if note else f"{header}{recent_section}"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(lang.t("btn_draw"), callback_data=f"draw:{list_name}"),
         InlineKeyboardButton(lang.t("btn_add"), callback_data=f"add:{list_name}")],
        [InlineKeyboardButton(lang.t("btn_remove"), callback_data=f"remove:{list_name}"),
         InlineKeyboardButton(lang.t("btn_edit"), callback_data=f"edit:{list_name}"),
         InlineKeyboardButton(lang.t("btn_view"), callback_data=f"list:{list_name}:0")],
        [InlineKeyboardButton(lang.t("btn_stats"), callback_data=f"stats:{list_name}"),
         InlineKeyboardButton(lang.t("btn_default"), callback_data=f"set_default:{list_name}"),
         InlineKeyboardButton(lang.t("btn_share"), callback_data=f"share:{list_name}")],
        [InlineKeyboardButton(lang.t("btn_back"), callback_data="back")],
    ])
    return text, markup


def _render_share_panel(chat_id: int, list_name: str, owner_chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """Build the sharing management panel for a list."""
    from database import get_connection
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (owner_chat_id, list_name),
        ).fetchone()
    list_id = row["id"] if row else None
    guests = get_list_shares(list_id) if list_id else []
    is_owner = chat_id == owner_chat_id
    def _fmt_guest(g: int) -> str:
        n = lookup_name(g)
        return f"  • {n} (`{g}`)" if n else f"  • `{g}`"
    guest_lines = "\n".join(_fmt_guest(g) for g in guests) if guests else lang.t("share_no_guests")
    role = lang.t("share_role_owner") if is_owner else lang.t("share_role_guest")
    owner_label = lookup_name(owner_chat_id)
    owner_str = f"{owner_label} (`{owner_chat_id}`)" if owner_label else f"`{owner_chat_id}`"
    owner_line = "" if is_owner else lang.t("share_owner_line", owner=owner_str)
    text = (
        f"*{lang.t('share_title', list_name=list_name)}*\n\n"
        f"{lang.t('share_your_id', chat_id=chat_id)}\n"
        f"{lang.t('share_role_label', role=role)}\n"
        f"{owner_line}\n"
        f"{lang.t('share_guests_header')}\n{guest_lines}"
    )
    buttons: list[list[InlineKeyboardButton]] = []
    if is_owner:
        buttons.append([
            InlineKeyboardButton(lang.t("btn_invite"), callback_data=f"share_invite:{list_name}"),
            InlineKeyboardButton(lang.t("btn_remove_guest"), callback_data=f"share_remove:{list_name}"),
        ])
        buttons.append([
            InlineKeyboardButton(lang.t("btn_transfer"), callback_data=f"share_transfer:{list_name}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(lang.t("btn_leave"), callback_data=f"share_leave:{list_name}"),
        ])
    buttons.append([InlineKeyboardButton(lang.t("btn_back"), callback_data=f"open:{list_name}")])
    return text, InlineKeyboardMarkup(buttons)


async def _notify(bot, chat_id: int, text: str, thread_id: int | None) -> None:
    """Send an HTML notification to the correct chat thread."""
    await bot.send_message(chat_id, text, parse_mode="HTML", message_thread_id=thread_id)


def _force_reply_msg(user, body: str, bold_text: str) -> tuple[str, list[MessageEntity]]:
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


def _first_name(name: str) -> str:
    """Return the part of a name before the first whitespace, symbol, or punctuation."""
    m = re.match(r"[^\s\W]+", name, re.UNICODE)
    return m.group(0) if m else name




async def _send_force_reply(
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
    msg_text, entities = _force_reply_msg(user, body, bold_text)
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


async def _cleanup_reply_messages(bot, chat_id: int, prompt_msg_id: int, user_msg_id: int) -> None:
    """Delete the ForceReply prompt and the user's reply from chat."""
    await bot.delete_message(chat_id, prompt_msg_id)
    await bot.delete_message(chat_id, user_msg_id)


async def _do_draw(
    bot, chat_id: int, list_name: str, user_name: str, thread_id: int | None, notify_chat_id: int | None = None
) -> bool:
    """Draw a random prompt and notify. chat_id is the list owner; notify_chat_id is where to send the result."""
    prompt = draw_random_prompt(chat_id, list_name)
    if not prompt:
        return False
    added_by = _first_name(prompt["added_by_name"]) if prompt["added_by_name"] else ""
    author_line = lang.t("notify_drew_author", added_by=added_by) if added_by else ""
    msg = lang.t(
        "notify_drew", user=_first_name(user_name), list_name=list_name, text=prompt["text"], author_line=author_line
    )
    await _notify(bot, notify_chat_id if notify_chat_id is not None else chat_id, msg, thread_id)
    return True


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
        upsert_user(chat_id, query.message.chat.title)

    if data == "back":
        text, markup = _render_lists_view(chat_id, chat_title)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("open:"):
        list_name = data[5:]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = _render_list_view(owner_chat_id, list_name)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("draw:"):
        list_name = data[5:]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        user_name = query.from_user.full_name if query.from_user else "Someone"
        if not await _do_draw(
            context.bot, owner_chat_id, list_name, user_name, query.message.message_thread_id, notify_chat_id=chat_id
        ):
            text, markup = _render_list_view(owner_chat_id, list_name, lang.t("err_all_drawn"))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
            return
        await query.message.delete()

    elif data.startswith("list:"):
        parts = data[5:].rsplit(":", 1)
        list_name = parts[0]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        page = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 0
        PAGE_SIZE = 50
        prompts = get_prompts(owner_chat_id, list_name)
        total = len(prompts)
        drawn = sum(1 for p in prompts if p["drawn"])
        start = page * PAGE_SIZE
        page_prompts = prompts[start:start + PAGE_SIZE]
        lines = "\n".join(f"{p['position']}. {p['text']}" for p in page_prompts) or lang.t("panel_empty")
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        paged = lang.t("panel_list_header_paged", total=total, drawn=drawn, page=page + 1, total_pages=total_pages)
        header = f"*{list_name}*  {paged}"
        text = f"{header}\n\n{lines}"
        _, base_markup = _render_list_view(owner_chat_id, list_name)
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
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        s = get_stats(owner_chat_id, list_name)
        if not s:
            await query.answer(lang.t("err_list_not_found"), show_alert=True)
            return
        user_lines = "\n".join(
            lang.t("stats_user_line", name=_first_name(r["name"]), count=r["count"]) for r in s["by_user"]
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
        _, markup = _render_list_view(owner_chat_id, list_name)
        await query.edit_message_text(stats_text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("remove:"):
        list_name = data[7:]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        if not get_prompts(owner_chat_id, list_name):
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(lang.t("btn_delete_list"), callback_data=f"delete_list_confirm:{list_name}"),
                InlineKeyboardButton(lang.t("btn_back_cancel"), callback_data=f"open:{list_name}"),
            ]])
            await query.edit_message_text(
                lang.t("confirm_delete_prompt", list_name=list_name), reply_markup=markup, parse_mode="Markdown"
            )
            return
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "remove", lang.t("fr_remove_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("edit:"):
        list_name = data[5:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "edit", lang.t("fr_edit_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("add:"):
        list_name = data[4:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "add", lang.t("fr_add_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("set_default:"):
        list_name = data[12:]
        set_default_list(chat_id, list_name)
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = _render_list_view(owner_chat_id, list_name, lang.t("confirm_set_default", list_name=list_name))
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("delete_list_confirm:"):
        list_name = data[20:]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        if delete_list(owner_chat_id, list_name):
            text, markup = _render_lists_view(chat_id, lang.t("confirm_list_deleted", list_name=list_name))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        else:
            text, markup = _render_list_view(owner_chat_id, list_name, lang.t("err_cannot_delete"))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("share:"):
        list_name = data[6:]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("share_invite:"):
        list_name = data[13:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "share_invite", lang.t("fr_invite_body", chat_id=chat_id, list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("share_remove:"):
        list_name = data[13:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "share_remove", lang.t("fr_remove_guest_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("share_transfer:"):
        list_name = data[15:]
        await _send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "share_transfer", lang.t("fr_transfer_body", list_name=list_name),
            list_name, list_name=list_name,
        )

    elif data.startswith("share_leave:"):
        list_name = data[12:]
        owner_chat_id = resolve_list_owner(chat_id, list_name)
        if owner_chat_id:
            from database import get_connection
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
                    (owner_chat_id, list_name),
                ).fetchone()
            if row:
                remove_list_share(row["id"], chat_id)
        text, markup = _render_lists_view(chat_id, query.message.chat.title or "Lists")
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data == "new_list":
        await _send_force_reply(
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
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        user_name = msg.from_user.full_name if msg.from_user else ""
        upsert_user(msg.from_user.id, user_name)
        position = add_prompt(owner_chat_id, list_name, user_text, added_by_id=msg.from_user.id)
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await _notify(
            context.bot, chat_id,
            lang.t("notify_added", user=_first_name(user_name), position=position, list_name=list_name, text=user_text),
            msg.message_thread_id,
        )
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "remove":
        list_name = state["list_name"]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        if not user_text.isdigit():
            await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = _render_list_view(owner_chat_id, list_name, lang.t("err_not_a_number"))
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        position = int(user_text)
        removed = remove_prompt(owner_chat_id, list_name, position)
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        note = (
            lang.t("notify_removed", position=position, text=removed["text"])
            if removed
            else lang.t("err_no_item_at", position=position)
        )
        await _notify(context.bot, chat_id, note, msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "edit":
        list_name = state["list_name"]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        parts = user_text.split(None, 1)
        if parts[0].lower() == "rename":
            new_name = parts[1].strip() if len(parts) > 1 else ""
            await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            if not new_name:
                text, markup = _render_list_view(owner_chat_id, list_name, lang.t("err_rename_format"))
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
                return
            renamed = rename_list(owner_chat_id, list_name, new_name)
            if renamed:
                await _notify(
                    context.bot, chat_id,
                    lang.t("notify_renamed", old_name=list_name, new_name=new_name),
                    msg.message_thread_id,
                )
                text, markup = _render_list_view(owner_chat_id, new_name)
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
            else:
                text, markup = _render_list_view(owner_chat_id, list_name, lang.t("err_rename_exists", name=new_name))
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
            return
        if len(parts) < 2 or not parts[0].isdigit():
            await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = _render_list_view(owner_chat_id, list_name, lang.t("err_edit_format"))
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        position, new_text = int(parts[0]), parts[1].strip()
        user_name = msg.from_user.full_name if msg.from_user else ""
        updated = edit_prompt(owner_chat_id, list_name, position, new_text)
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if updated:
            await _notify(
                context.bot, chat_id,
                lang.t("notify_edited", user=_first_name(user_name), position=position, list_name=list_name, text=new_text),
                msg.message_thread_id,
            )
        else:
            await _notify(context.bot, chat_id, lang.t("err_no_item_at", position=position), msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "new_list":
        list_name = user_text
        text, markup = _render_list_view(chat_id, list_name, lang.t("confirm_list_created"))
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await context.bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_invite":
        list_name = state["list_name"]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        guest_id = int(user_text)
        from database import get_connection
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lists WHERE chat_id=? AND list_name=?", (owner_chat_id, list_name)
            ).fetchone()
        if row and add_list_share(row["id"], guest_id):
            note = lang.t("confirm_invite_ok", chat_id=guest_id, list_name=list_name)
        else:
            note = lang.t("err_invite_failed", chat_id=guest_id)
        text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_remove":
        list_name = state["list_name"]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        guest_id = int(user_text)
        from database import get_connection
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lists WHERE chat_id=? AND list_name=?", (owner_chat_id, list_name)
            ).fetchone()
        if row and remove_list_share(row["id"], guest_id):
            note = lang.t("confirm_remove_guest_ok", chat_id=guest_id, list_name=list_name)
        else:
            note = lang.t("err_remove_guest_failed", chat_id=guest_id)
        text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_transfer":
        list_name = state["list_name"]
        owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
        await _cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
            await context.bot.edit_message_text(
                text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
            )
            return
        new_owner_id = int(user_text)
        from database import get_connection
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lists WHERE chat_id=? AND list_name=?", (owner_chat_id, list_name)
            ).fetchone()
        if row and transfer_list_ownership(row["id"], new_owner_id):
            note = lang.t("confirm_transfer_ok", list_name=list_name, new_owner=new_owner_id)
            text, markup = _render_share_panel(chat_id, list_name, new_owner_id)
        else:
            note = lang.t("err_transfer_failed", chat_id=new_owner_id)
            text, markup = _render_share_panel(chat_id, list_name, owner_chat_id)
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
            owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
            text, markup = _render_list_view(owner_chat_id, list_name)
        else:
            chat_title = msg.chat.title or "Lists"
            text, markup = _render_lists_view(chat_id, chat_title)
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
    list_name = get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text(lang.t("err_no_default"), parse_mode="Markdown")
        return
    owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
    user_name = update.message.from_user.full_name if update.message.from_user else "Someone"
    if not await _do_draw(
        context.bot, owner_chat_id, list_name, user_name, update.message.message_thread_id, notify_chat_id=chat_id
    ):
        await update.message.reply_text(lang.t("err_list_empty", list_name=list_name), parse_mode="Markdown")
        return
    await update.message.delete()


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an item to the default list. Usage: /add <item text>"""
    chat_id = update.effective_chat.id
    list_name = get_default_list(chat_id)
    if not list_name:
        await update.message.reply_text(lang.t("err_no_default"), parse_mode="Markdown")
        return
    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await update.message.reply_text(lang.t("err_add_usage"), parse_mode="Markdown")
        return
    owner_chat_id = resolve_list_owner(chat_id, list_name) or chat_id
    user_name = update.message.from_user.full_name if update.message.from_user else ""
    upsert_user(update.message.from_user.id, user_name)
    position = add_prompt(owner_chat_id, list_name, text, added_by_id=update.message.from_user.id)
    await update.message.delete()
    await _notify(
        context.bot, chat_id,
        lang.t("notify_added", user=_first_name(user_name), position=position, list_name=list_name, text=text),
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
    init_db()
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
