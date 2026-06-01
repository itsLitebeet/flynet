"""Show / hide the Telegram reply keyboard (bottom menu buttons).

Use Telegram's built-in behaviour:
- attach ``ReplyKeyboardMarkup`` on a normal ``message.answer(...)`` to show the menu
- attach ``ReplyKeyboardRemove()`` to hide it (user can also hide via the client UI)
"""

from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardMarkup

from app import keyboards


async def hide_bottom_keyboard(message: Message) -> None:
    """Hide the custom reply keyboard (``ReplyKeyboardRemove``)."""
    await message.answer(
        keyboards.HIDE_KEYBOARD_REPLY_TEXT,
        reply_markup=keyboards.hide_reply_keyboard(),
    )
