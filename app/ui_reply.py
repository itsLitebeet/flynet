"""Show / hide the Telegram reply keyboard (bottom menu buttons).

Use Telegram's built-in behaviour:
- attach ``ReplyKeyboardMarkup`` on a normal ``message.answer(...)`` to show the menu
- attach ``ReplyKeyboardRemove()`` on a message that has real (non-empty) text
- attach inline keyboards on the same message via ``answer_with_inline_keyboard``
"""

from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from app import keyboards


async def answer_with_inline_keyboard(
    message: Message,
    text: str,
    inline_markup: InlineKeyboardMarkup,
    *,
    parse_mode: str | ParseMode | None = None,
) -> Message:
    """Remove the reply keyboard and show inline buttons (one user-visible message)."""
    sent = await message.answer(
        text,
        reply_markup=keyboards.hide_reply_keyboard(),
        parse_mode=parse_mode,
    )
    try:
        await sent.edit_reply_markup(reply_markup=inline_markup)
    except TelegramBadRequest:
        sent = await message.answer(
            text,
            reply_markup=inline_markup,
            parse_mode=parse_mode,
        )
    return sent


async def answer_removing_reply_keyboard(
    message: Message,
    text: str,
    *,
    parse_mode: str | ParseMode | None = None,
) -> Message:
    """Send text and remove the bottom reply keyboard."""
    return await message.answer(
        text,
        reply_markup=keyboards.hide_reply_keyboard(),
        parse_mode=parse_mode,
    )
