
from telegram import Update
from telegram.ext import ContextTypes

import db
import i18n as lang
from messaging import cleanup_reply_messages, notify
from text import first_name
from ui import views


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
            text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_not_a_number"))
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
                text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_rename_format"))
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
                text, markup = views.render_list_view(owner_chat_id, new_name)
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
            else:
                text, markup = views.render_list_view(
                    owner_chat_id, list_name, lang.t("err_rename_exists", name=new_name)
                )
                await context.bot.edit_message_text(
                    text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
                )
            return
        if len(parts) < 2 or not parts[0].isdigit():
            await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
            text, markup = views.render_list_view(owner_chat_id, list_name, lang.t("err_edit_format"))
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
                lang.t("notify_edited", user=first_name(user_name), position=position,
                       list_name=list_name, text=new_text),
                msg.message_thread_id,
            )
        else:
            await notify(context.bot, chat_id, lang.t("err_no_item_at", position=position), msg.message_thread_id)
        await context.bot.delete_message(chat_id, panel_msg_id)

    elif state["action"] == "new_list":
        list_name = user_text
        text, markup = views.render_list_view(chat_id, list_name, lang.t("confirm_list_created"))
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        await context.bot.edit_message_text(
            text, chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_invite":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
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
        text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_remove":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
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
        text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )

    elif state["action"] == "share_transfer":
        list_name = state["list_name"]
        owner_chat_id = db.resolve_list_owner(chat_id, list_name) or chat_id
        await cleanup_reply_messages(context.bot, chat_id, prompt_msg_id, msg.message_id)
        if not user_text.lstrip("-").isdigit():
            text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
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
            text, markup = views.render_share_panel(chat_id, list_name, new_owner_id)
        else:
            note = lang.t("err_transfer_failed", chat_id=new_owner_id)
            text, markup = views.render_share_panel(chat_id, list_name, owner_chat_id)
        await context.bot.edit_message_text(
            f"{note}\n\n{text}", chat_id=chat_id, message_id=panel_msg_id, reply_markup=markup, parse_mode="Markdown"
        )