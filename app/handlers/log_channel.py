"""Admin command /logchannel — bind a Telegram channel for audit logs."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app import texts
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import admin_from_message
from app.logs import resolve_forwarded_channel_id, try_bind_log_channel

router = Router(name="log_channel")


class LogChannelFlow(StatesGroup):
    waiting_channel = State()


@router.message(Command("logchannel"), StateFilter(None))
async def cmd_logchannel(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not admin_from_message(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    if raw.lower() in ("off", "-", "0", "none"):
        db.set_log_channel_id(None)
        await message.answer(texts.LOG_CHANNEL_CLEARED)
        return

    if raw:
        try:
            chat_id = int(raw)
        except ValueError:
            await message.answer(texts.LOG_CHANNEL_USAGE)
            return
        ok, reply = await try_bind_log_channel(bot, db, chat_id)
        await message.answer(reply)
        if not ok:
            return
        return

    await state.set_state(LogChannelFlow.waiting_channel)
    await message.answer(texts.LOG_CHANNEL_PROMPT)


@router.message(Command("cancel"), StateFilter(LogChannelFlow))
async def cmd_cancel_logchannel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED)


@router.message(StateFilter(LogChannelFlow.waiting_channel))
async def on_logchannel_input(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not admin_from_message(message, settings):
        return

    chat_id = resolve_forwarded_channel_id(message)
    if chat_id is None:
        text = (message.text or "").strip()
        if text.lstrip("-").isdigit():
            chat_id = int(text)
        else:
            await message.answer(texts.LOG_CHANNEL_NEED_FORWARD)
            return

    ok, reply = await try_bind_log_channel(bot, db, chat_id)
    await message.answer(reply)
    if ok:
        await state.clear()
