from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database


router = Router(name="support")
log = logging.getLogger(__name__)

MAX_TICKET_LEN = 2000


class SupportFlow(StatesGroup):
    waiting_for_message = State()


@router.callback_query(F.data == keyboards.CB_MAIN_SUPPORT)
async def cb_open_support(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportFlow.waiting_for_message)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.SUPPORT_PROMPT, reply_markup=keyboards.cancel_support()
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_CANCEL_SUPPORT)
async def cb_cancel_support(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.CANCELLED, reply_markup=keyboards.main_menu()
        )
    await callback.answer()


@router.message(StateFilter(SupportFlow.waiting_for_message))
async def on_support_message(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    text = (message.text or message.caption or "").strip()
    if not text:
        await message.answer(texts.SUPPORT_EMPTY)
        return
    if len(text) > MAX_TICKET_LEN:
        await message.answer(texts.SUPPORT_TOO_LONG)
        return

    user = message.from_user
    if user is None:
        await state.clear()
        return

    ticket_id = db.create_ticket(user_id=user.id, message=text)
    await state.clear()
    await message.answer(texts.SUPPORT_SENT, reply_markup=keyboards.main_menu())

    full_name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
    notify = texts.NEW_TICKET_NOTIFY.format(
        ticket_id=ticket_id,
        user_id=user.id,
        full_name=escape(full_name),
        message=escape(text),
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, notify)
        except Exception:  # noqa: BLE001
            log.exception("Failed to notify admin %s about ticket %s", admin_id, ticket_id)
