"""Show / hide the Telegram reply keyboard (bottom menu buttons)."""

from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardMarkup

from app import keyboards


KEYBOARD_UPDATE_PLACEHOLDER = "."


async def _send_keyboard_update(message: Message, reply_markup) -> None:
    sent = await message.answer(KEYBOARD_UPDATE_PLACEHOLDER, reply_markup=reply_markup)
    try:
        await sent.delete()
    except Exception:  # noqa: BLE001 - deleting can fail for old clients/permissions.
        pass


async def hide_bottom_keyboard(message: Message) -> None:
    """Remove custom reply keyboard buttons in this chat."""
    await _send_keyboard_update(message, keyboards.hide_reply_keyboard())


async def show_bottom_keyboard(message: Message, markup: ReplyKeyboardMarkup) -> None:
    """Show (or restore) custom reply keyboard buttons."""
    await _send_keyboard_update(message, markup)
