from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app import texts
from app.db import Location


# ---------- callback data namespaces ----------
# Top menu
CB_MAIN_BUY           = "main:buy"
CB_MAIN_MY_SERVICES   = "main:my"
CB_MAIN_ACCOUNT       = "main:account"
CB_MAIN_SUPPORT       = "main:support"
CB_MAIN_HELP          = "main:help"
CB_MAIN_ABOUT         = "main:about"
CB_MAIN_HOME          = "main:home"

# Order flow
CB_LOC_PREFIX     = "loc:"          # loc:<location_id>
CB_VOL_PREFIX     = "vol:"          # vol:<gb> or vol:custom
CB_VOL_CUSTOM     = "vol:custom"
CB_DUR_PREFIX     = "dur:"          # dur:<days>
CB_ORDER_CONFIRM  = "ord:confirm"   # final confirmation of summary
CB_ORDER_CANCEL   = "ord:cancel"
CB_ORDER_BACK_LOC = "ord:back:loc"
CB_ORDER_BACK_VOL = "ord:back:vol"
CB_ORDER_BACK_DUR = "ord:back:dur"

# Support
CB_CANCEL_SUPPORT = "support:cancel"

# Admin review
CB_ADMIN_ACCEPT_PREFIX  = "adm:acc:"   # adm:acc:<order_id>
CB_ADMIN_DECLINE_PREFIX = "adm:dec:"   # adm:dec:<order_id>

# Admin destructive actions (require explicit confirmation)
CB_PURGE_CONFIRM_PREFIX = "adm:prg:ok:"  # adm:prg:ok:<location_id>
CB_PURGE_CANCEL         = "adm:prg:no"

# My services
CB_MY_LIST                  = "my:list"
CB_MY_DETAIL_PREFIX         = "my:o:"        # my:o:<order_id>
CB_MY_CONFIGS_PREFIX        = "my:cfg:"      # my:cfg:<order_id>
CB_MY_USAGE_PREFIX          = "my:use:"      # my:use:<order_id>
CB_MY_TOGGLE_PREFIX         = "my:tog:"      # my:tog:<order_id>
CB_MY_RENAME_PREFIX         = "my:ren:"      # my:ren:<order_id>
CB_MY_REGEN_PREFIX          = "my:rg:"       # my:rg:<order_id>      (asks confirmation)
CB_MY_REGEN_CONFIRM_PREFIX  = "my:rg!ok:"    # my:rg!ok:<order_id>   (actually regen)


# ---------- reply keyboard (bottom menu, replaces phone keyboard) ----------
def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom buttons — main navigation for buyers."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=texts.BTN_BUY),
                KeyboardButton(text=texts.BTN_MY_SERVICES),
            ],
            [
                KeyboardButton(text=texts.BTN_MY_ACCOUNT),
                KeyboardButton(text=texts.BTN_SUPPORT),
            ],
            [
                KeyboardButton(text=texts.BTN_HELP),
                KeyboardButton(text=texts.BTN_ABOUT),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def hide_reply_keyboard() -> ReplyKeyboardRemove:
    """Hide bottom buttons during wizards (order, support, rename)."""
    return ReplyKeyboardRemove()


# All main-menu button labels — use with F.text.in_(...) + StateFilter(None).
MAIN_MENU_BUTTONS = frozenset({
    texts.BTN_BUY,
    texts.BTN_MY_SERVICES,
    texts.BTN_MY_ACCOUNT,
    texts.BTN_SUPPORT,
    texts.BTN_HELP,
    texts.BTN_ABOUT,
})


# ---------- inline keyboards (inside messages / wizards) ----------
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_BUY,         callback_data=CB_MAIN_BUY),
                InlineKeyboardButton(text=texts.BTN_MY_SERVICES, callback_data=CB_MAIN_MY_SERVICES),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_MY_ACCOUNT, callback_data=CB_MAIN_ACCOUNT),
                InlineKeyboardButton(text=texts.BTN_SUPPORT,    callback_data=CB_MAIN_SUPPORT),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_HELP,  callback_data=CB_MAIN_HELP),
                InlineKeyboardButton(text=texts.BTN_ABOUT, callback_data=CB_MAIN_ABOUT),
            ],
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME)]
        ]
    )


# ---------- order flow ----------
def locations(locations: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locations:
        rows.append(
            [InlineKeyboardButton(text=loc.name, callback_data=f"{CB_LOC_PREFIX}{loc.id}")]
        )
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def volumes() -> InlineKeyboardMarkup:
    row: list[InlineKeyboardButton] = []
    for gb in texts.VOLUME_PRESETS_GB:
        row.append(
            InlineKeyboardButton(text=f"{gb} GB", callback_data=f"{CB_VOL_PREFIX}{gb}")
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text=texts.BTN_CUSTOM, callback_data=CB_VOL_CUSTOM)],
            [InlineKeyboardButton(text=texts.BTN_BACK,   callback_data=CB_ORDER_BACK_LOC)],
        ]
    )


def durations() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=f"{d} روزه", callback_data=f"{CB_DUR_PREFIX}{d}")
        for d in texts.DURATION_PRESETS_DAYS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_VOL)],
        ]
    )


def confirm_order() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data=CB_ORDER_CONFIRM)],
            [InlineKeyboardButton(text=texts.BTN_BACK,    callback_data=CB_ORDER_BACK_DUR)],
            [InlineKeyboardButton(text=texts.BTN_CANCEL,  callback_data=CB_ORDER_CANCEL)],
        ]
    )


def cancel_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ORDER_CANCEL)]
        ]
    )


# ---------- support ----------
def cancel_support() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_CANCEL_SUPPORT)]
        ]
    )


# ---------- admin destructive confirmation ----------
def purge_confirm(location_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ بله، پاک کن",
                    callback_data=f"{CB_PURGE_CONFIRM_PREFIX}{location_id}",
                ),
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data=CB_PURGE_CANCEL
                ),
            ]
        ]
    )


# ---------- my services ----------
def my_services_list(orders: list[dict]) -> InlineKeyboardMarkup:
    """`orders` is a list of dicts with keys: id, label."""
    rows: list[list[InlineKeyboardButton]] = []
    for o in orders:
        rows.append([
            InlineKeyboardButton(text=o["label"], callback_data=f"{CB_MY_DETAIL_PREFIX}{o['id']}")
        ])
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_service_detail(order_id: int, *, provisioned: bool, enabled: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if provisioned:
        rows.append([
            InlineKeyboardButton(text=texts.BTN_VIEW_CONFIGS, callback_data=f"{CB_MY_CONFIGS_PREFIX}{order_id}"),
            InlineKeyboardButton(text=texts.BTN_VIEW_USAGE,   callback_data=f"{CB_MY_USAGE_PREFIX}{order_id}"),
        ])
        toggle_text = texts.BTN_TOGGLE_OFF if enabled else texts.BTN_TOGGLE_ON
        rows.append([
            InlineKeyboardButton(text=toggle_text,        callback_data=f"{CB_MY_TOGGLE_PREFIX}{order_id}"),
            InlineKeyboardButton(text=texts.BTN_RENAME,   callback_data=f"{CB_MY_RENAME_PREFIX}{order_id}"),
        ])
        rows.append([
            InlineKeyboardButton(text=texts.BTN_REGEN,    callback_data=f"{CB_MY_REGEN_PREFIX}{order_id}"),
        ])
    else:
        # Non-provisioned orders only get a rename + back so users can
        # at least label their pending/declined orders for reference.
        rows.append([
            InlineKeyboardButton(text=texts.BTN_RENAME, callback_data=f"{CB_MY_RENAME_PREFIX}{order_id}"),
        ])
    rows.append([InlineKeyboardButton(text="🔙 لیست سرویس‌ها", callback_data=CB_MY_LIST)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_service(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🔙 جزئیات سرویس", callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}")
        ]]
    )


def regen_confirm(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_REGEN_CONFIRM,
                                     callback_data=f"{CB_MY_REGEN_CONFIRM_PREFIX}{order_id}"),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_BACK,
                                     callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}"),
            ],
        ]
    )


# ---------- admin review ----------
def admin_review(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_ACCEPT, callback_data=f"{CB_ADMIN_ACCEPT_PREFIX}{order_id}"
                ),
                InlineKeyboardButton(
                    text=texts.BTN_DECLINE, callback_data=f"{CB_ADMIN_DECLINE_PREFIX}{order_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.BTN_VIEW_USER, url=f"tg://user?id={user_id}"
                )
            ],
        ]
    )
