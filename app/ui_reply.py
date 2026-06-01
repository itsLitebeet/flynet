"""Show / hide the Telegram reply keyboard (bottom menu buttons)."""

from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardMarkup

from app import keyboards


async def hide_bottom_keyboard(message: Message) -> None:
    """Remove custom reply keyboard buttons in this chat."""
    await message.answer("\u200b", reply_markup=keyboards.hide_reply_keyboard())


async def show_bottom_keyboard(message: Message, markup: ReplyKeyboardMarkup) -> None:
    """Show (or restore) custom reply keyboard buttons."""
    await message.answer("\u200b", reply_markup=markup)
