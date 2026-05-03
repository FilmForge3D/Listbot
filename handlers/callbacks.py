from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TimedOut
from telegram.ext import ContextTypes

import db
import i18n as lang
from actions import do_draw
from messaging import send_force_reply
from text import first_name
from ui import views


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
        text, markup = views.render_lists_view(chat_id, chat_title)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("open:"):
        list_name = data[5:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = views.render_list_view(owner_chat_id, list_name)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("draw:"):
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
        _, markup = views.render_list_view(owner_chat_id, list_name)
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
        text, markup = views.render_list_view(
            owner_chat_id, list_name, lang.t("confirm_set_default", list_name=list_name)
        )
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("db.delete_list_confirm:"):
        list_name = data[20:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        if db.delete_list(owner_chat_id, list_name):
            text, markup = views.render_lists_view(chat_id, lang.t("confirm_list_deleted", list_name=list_name))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        else:
            text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_cannot_delete"))
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("share:"):
        list_name = data[6:]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
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
        text, markup = views.render_lists_view(chat_id, query.message.chat.title or "Lists")
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data == "new_list":
        await send_force_reply(
            context, chat_id, query.message.message_thread_id, query.message.message_id,
            query.from_user, "new_list", lang.t("fr_new_list_body"),
        )