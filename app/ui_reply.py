"""Show / hide the Telegram reply keyboard (bottom menu buttons)."""

from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardMarkup

from app import keyboards

# Invisible character — keeps the bubble minimal when re-showing the keyboard.
_KEYBOARD_HINT = "\u200b"


async def show_bottom_keyboard(message: Message, markup: ReplyKeyboardMarkup) -> None:
    """Show or restore reply keyboard.

    Important: do NOT delete this message afterward. Telegram removes the custom
    keyboard when the message that attached it is deleted.
    """
    await message.answer(_KEYBOARD_HINT, reply_markup=markup)


async def hide_bottom_keyboard(message: Message) -> None:
    """Remove custom reply keyboard buttons in this chat."""
    await message.answer(_KEYBOARD_HINT, reply_markup=keyboards.hide_reply_keyboard())
