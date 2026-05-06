from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import db
import i18n as lang


def render_lists_view(chat_id: int, title: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build the list-selection panel text and keyboard."""
    owned = db.get_list_names(chat_id)
    shared = db.get_shared_lists(chat_id)
    default = db.get_default_list(chat_id)
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


def render_list_view(chat_id: int, list_name: str, note: str = "") -> tuple[str, InlineKeyboardMarkup]:
    """Build the detail panel for a single named list."""
    prompts = db.get_prompts(chat_id, list_name)
    total = len(prompts)
    drawn = sum(1 for p in prompts if p["drawn"])
    header = f"*{list_name}*  {lang.t('panel_list_header', total=total, drawn=drawn)}"
    recent = db.get_recently_drawn_prompts(chat_id, list_name)
    if recent:
        lines = "\n".join(f"• {p['text']}" for p in recent)
        recent_section = f"\n\n*{lang.t('panel_recent_header')}*\n{lines}"
    else:
        recent_section = ""
    text = f"{header}{recent_section}\n\n{note}" if note else f"{header}{recent_section}"
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(lang.t("btn_draw"), callback_data=f"draw:{list_name}"),
                InlineKeyboardButton(lang.t("btn_add"), callback_data=f"add:{list_name}"),
            ],
            [
                InlineKeyboardButton(lang.t("btn_remove"), callback_data=f"remove:{list_name}"),
                InlineKeyboardButton(lang.t("btn_edit"), callback_data=f"edit:{list_name}"),
                InlineKeyboardButton(lang.t("btn_view"), callback_data=f"list:{list_name}:0"),
            ],
            [
                InlineKeyboardButton(lang.t("btn_stats"), callback_data=f"stats:{list_name}"),
                InlineKeyboardButton(lang.t("btn_default"), callback_data=f"set_default:{list_name}"),
                InlineKeyboardButton(lang.t("btn_share"), callback_data=f"share:{list_name}"),
            ],
            [InlineKeyboardButton(lang.t("btn_back"), callback_data="back")],
        ]
    )
    return text, markup


def render_share_panel(chat_id: int, list_name: str, owner_chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """Build the sharing management panel for a list."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM lists WHERE chat_id = ? AND list_name = ?",
            (owner_chat_id, list_name),
        ).fetchone()
    list_id = row["id"] if row else None
    guests = db.get_list_shares(list_id) if list_id else []
    is_owner = chat_id == owner_chat_id

    def _fmt_guest(g: int) -> str:
        n = db.lookup_name(g)
        return f"  • {n} (`{g}`)" if n else f"  • `{g}`"

    guest_lines = "\n".join(_fmt_guest(g) for g in guests) if guests else lang.t("share_no_guests")
    role = lang.t("share_role_owner") if is_owner else lang.t("share_role_guest")
    owner_label = db.lookup_name(owner_chat_id)
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
        buttons.append(
            [
                InlineKeyboardButton(lang.t("btn_invite"), callback_data=f"share_invite:{list_name}"),
                InlineKeyboardButton(lang.t("btn_remove_guest"), callback_data=f"share_remove:{list_name}"),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(lang.t("btn_transfer"), callback_data=f"share_transfer:{list_name}"),
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(lang.t("btn_leave"), callback_data=f"share_leave:{list_name}"),
            ]
        )
    buttons.append([InlineKeyboardButton(lang.t("btn_back"), callback_data=f"open:{list_name}")])
    return text, InlineKeyboardMarkup(buttons)
