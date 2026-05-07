from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TimedOut
from telegram.ext import ContextTypes

import db
import i18n as lang
from actions import do_draw
from messaging import send_force_reply
from text import first_name
from ui import views

PAGE_SIZE = 50


async def _prompt_reply(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    action: str,
    body: str,
    bold_text: str = "",
    list_name: str | None = None,
) -> None:
    """Send a ForceReply with the query's boilerplate args pre-bound."""
    await send_force_reply(
        context,
        chat_id,
        query.message.message_thread_id,
        query.message.message_id,
        query.from_user,
        action,
        body,
        bold_text,
        list_name,
    )


async def _handle_back(query: CallbackQuery, chat_id: int, chat_title: str) -> None:
    """Navigate back to the lists overview."""
    text, markup = views.render_lists_view(chat_id, chat_title)
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def _handle_open(query: CallbackQuery, chat_id: int, data: str) -> None:
    """Open the panel for a specific list."""
    list_name = data[5:]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    text, markup = views.render_list_view(owner_chat_id, list_name)
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def _handle_draw(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Draw a random prompt from the list."""
    list_name = data[5:]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    user_name = query.from_user.full_name if query.from_user else "Someone"
    if not await do_draw(
        context.bot, owner_chat_id, list_name, user_name, query.message.message_thread_id, notify_chat_id=chat_id
    ):
        text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_all_drawn"))
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        return
    await query.message.delete()


async def _handle_list_page(query: CallbackQuery, chat_id: int, data: str) -> None:
    """Render a paginated prompt list."""
    parts = data[5:].rsplit(":", 1)
    list_name = parts[0]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    page = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 0
    prompts = db.get_prompts(owner_chat_id, list_name)
    total = len(prompts)
    drawn = sum(1 for p in prompts if p["drawn"])
    start = page * PAGE_SIZE
    page_prompts = prompts[start : start + PAGE_SIZE]
    lines = "\n".join(f"{p['position']}. {p['text']}" for p in page_prompts) or lang.t("panel_empty")
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    paged = lang.t("panel_list_header_paged", total=total, drawn=drawn, page=page + 1, total_pages=total_pages)
    text = f"*{list_name}*  {paged}\n\n{lines}"
    _, base_markup = views.render_list_view(owner_chat_id, list_name)
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


async def _handle_stats(query: CallbackQuery, chat_id: int, data: str) -> None:
    """Render draw statistics for a list."""
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
    _, markup = views.render_list_view(owner_chat_id, list_name)
    await query.edit_message_text(stats_text, reply_markup=markup, parse_mode="Markdown")


async def _handle_remove_prompt(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt for a position to remove, or offer list deletion if the list is empty."""
    list_name = data[7:]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    if not db.get_prompts(owner_chat_id, list_name):
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        lang.t("btn_delete_list"), callback_data=f"db.delete_list_confirm:{list_name}"
                    ),
                    InlineKeyboardButton(lang.t("btn_back_cancel"), callback_data=f"open:{list_name}"),
                ]
            ]
        )
        await query.edit_message_text(
            lang.t("confirm_delete_prompt", list_name=list_name), reply_markup=markup, parse_mode="Markdown"
        )
        return
    await _prompt_reply(query, context, chat_id, "remove", lang.t("fr_remove_body", list_name=list_name), list_name, list_name)


async def _handle_edit_prompt(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a ForceReply prompt to edit a prompt or rename the list."""
    list_name = data[5:]
    await _prompt_reply(query, context, chat_id, "edit", lang.t("fr_edit_body", list_name=list_name), list_name, list_name)


async def _handle_add_prompt(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a ForceReply prompt to add a new prompt."""
    list_name = data[4:]
    await _prompt_reply(query, context, chat_id, "add", lang.t("fr_add_body", list_name=list_name), list_name, list_name)


async def _handle_set_default(query: CallbackQuery, chat_id: int, data: str) -> None:
    """Set the default list for this chat."""
    list_name = data[12:]
    db.set_default_list(chat_id, list_name)
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("confirm_set_default", list_name=list_name))
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def _handle_delete_list_confirm(query: CallbackQuery, chat_id: int, data: str) -> None:
    """Delete a list after explicit user confirmation."""
    list_name = data[23:]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    if db.delete_list(owner_chat_id, list_name):
        text, markup = views.render_lists_view(chat_id, lang.t("confirm_list_deleted", list_name=list_name))
    else:
        text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_cannot_delete"))
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def _handle_share_panel(query: CallbackQuery, chat_id: int, data: str) -> None:
    """Open the share management panel for a list."""
    list_name = data[6:]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
    text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def _handle_share_invite(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a ForceReply prompt to invite a chat to the list."""
    list_name = data[13:]
    await _prompt_reply(query, context, chat_id, "share_invite", lang.t("fr_invite_body", chat_id=chat_id, list_name=list_name), list_name, list_name)


async def _handle_share_remove(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a ForceReply prompt to remove a chat from the list."""
    list_name = data[13:]
    await _prompt_reply(query, context, chat_id, "share_remove", lang.t("fr_remove_guest_body", list_name=list_name), list_name, list_name)


async def _handle_share_transfer(query: CallbackQuery, chat_id: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a ForceReply prompt to transfer list ownership."""
    list_name = data[15:]
    await _prompt_reply(query, context, chat_id, "share_transfer", lang.t("fr_transfer_body", list_name=list_name), list_name, list_name)


async def _handle_share_leave(query: CallbackQuery, chat_id: int, data: str, chat_title: str) -> None:
    """Remove this chat from a shared list."""
    list_name = data[12:]
    owner_chat_id = db.resolve_list_owner(chat_id, list_name)
    if owner_chat_id:
        list_id = db.get_list_id(owner_chat_id, list_name)
        if list_id:
            db.remove_list_share(list_id, chat_id)
    text, markup = views.render_lists_view(chat_id, chat_title)
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def _handle_new_list(query: CallbackQuery, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a ForceReply prompt to create a new list."""
    await _prompt_reply(query, context, chat_id, "new_list", lang.t("fr_new_list_body"))


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
        await _handle_back(query, chat_id, chat_title)
    elif data.startswith("open:"):
        await _handle_open(query, chat_id, data)
    elif data.startswith("draw:"):
        await _handle_draw(query, chat_id, data, context)
    elif data.startswith("list:"):
        await _handle_list_page(query, chat_id, data)
    elif data.startswith("stats:"):
        await _handle_stats(query, chat_id, data)
    elif data.startswith("remove:"):
        await _handle_remove_prompt(query, chat_id, data, context)
    elif data.startswith("edit:"):
        await _handle_edit_prompt(query, chat_id, data, context)
    elif data.startswith("add:"):
        await _handle_add_prompt(query, chat_id, data, context)
    elif data.startswith("set_default:"):
        await _handle_set_default(query, chat_id, data)
    elif data.startswith("db.delete_list_confirm:"):
        await _handle_delete_list_confirm(query, chat_id, data)
    elif data.startswith("share:"):
        await _handle_share_panel(query, chat_id, data)
    elif data.startswith("share_invite:"):
        await _handle_share_invite(query, chat_id, data, context)
    elif data.startswith("share_remove:"):
        await _handle_share_remove(query, chat_id, data, context)
    elif data.startswith("share_transfer:"):
        await _handle_share_transfer(query, chat_id, data, context)
    elif data.startswith("share_leave:"):
        await _handle_share_leave(query, chat_id, data, chat_title)
    elif data == "new_list":
        await _handle_new_list(query, chat_id, context)
