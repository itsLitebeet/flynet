from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.db import Database


router = Router(name="start")


async def _show_menu(message: Message) -> None:
    await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _show_menu(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP, reply_markup=keyboards.back_to_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())


@router.callback_query(F.data == keyboards.CB_MAIN_HOME)
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.WELCOME, reply_markup=keyboards.main_menu())
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_MAIN_HELP)
async def cb_help(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.HELP, reply_markup=keyboards.back_to_menu())
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_MAIN_ABOUT)
async def cb_about(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.ABOUT, reply_markup=keyboards.back_to_menu())
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_MAIN_ACCOUNT)
async def cb_account(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return

    row = db.get_user(user.id)
    created_at = row["created_at"] if row else "—"

    full_name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
    username = f"@{user.username}" if user.username else "—"

    text = texts.ACCOUNT_INFO.format(
        user_id=user.id,
        username=username,
        full_name=full_name,
        created_at=created_at,
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboards.back_to_menu())
    await callback.answer()
