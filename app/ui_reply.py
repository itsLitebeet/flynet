"""Show / hide the Telegram reply keyboard (bottom menu buttons)."""

from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardMarkup

from app import keyboards


KEYBOARD_UPDATE_PLACEHOLDER = "."


async def hide_bottom_keyboard(message: Message) -> None:
    """Remove custom reply keyboard buttons in this chat."""
    await message.answer(
        KEYBOARD_UPDATE_PLACEHOLDER,
        reply_markup=keyboards.hide_reply_keyboard(),
    )


async def show_bottom_keyboard(message: Message, markup: ReplyKeyboardMarkup) -> None:
    """Show (or restore) custom reply keyboard buttons."""
    await message.answer(KEYBOARD_UPDATE_PLACEHOLDER, reply_markup=markup)
