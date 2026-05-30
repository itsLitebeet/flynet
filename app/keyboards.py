from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import texts
from app.db import Location


# ---------- callback data namespaces ----------
# Top menu
CB_MAIN_BUY     = "main:buy"
CB_MAIN_ACCOUNT = "main:account"
CB_MAIN_SUPPORT = "main:support"
CB_MAIN_HELP    = "main:help"
CB_MAIN_ABOUT   = "main:about"
CB_MAIN_HOME    = "main:home"

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


# ---------- main menu ----------
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_BUY,        callback_data=CB_MAIN_BUY),
                InlineKeyboardButton(text=texts.BTN_MY_ACCOUNT, callback_data=CB_MAIN_ACCOUNT),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_SUPPORT, callback_data=CB_MAIN_SUPPORT),
                InlineKeyboardButton(text=texts.BTN_HELP,    callback_data=CB_MAIN_HELP),
            ],
            [InlineKeyboardButton(text=texts.BTN_ABOUT, callback_data=CB_MAIN_ABOUT)],
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
