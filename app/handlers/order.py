"""Multi-step order flow:

  location -> volume (preset or custom) -> duration -> review/confirm
           -> payment instructions (awaiting_payment)
           -> user uploads receipt photo (awaiting_review)
           -> admin gets notified with Accept/Decline buttons
"""

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


router = Router(name="order")
log = logging.getLogger(__name__)


class OrderFlow(StatesGroup):
    picking_location    = State()
    picking_volume      = State()
    entering_custom_vol = State()
    picking_duration    = State()
    reviewing           = State()
    awaiting_receipt    = State()


# ---------- helpers ----------
async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup)
            return
        except Exception:  # noqa: BLE001 — message may be uneditable (e.g. has a photo)
            pass
    if callback.message is not None:
        await callback.message.answer(text, reply_markup=reply_markup)


def _calc_price_for(db: Database, volume_gb: int, duration_days: int) -> int:
    base, per_gb, per_day = db.get_pricing()
    return texts.calc_price(volume_gb, duration_days, base, per_gb, per_day)


async def _show_locations(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    locs = db.list_locations(only_enabled=True)
    if not locs:
        await _edit_or_answer(callback, texts.NO_LOCATIONS_USER, keyboards.back_to_menu())
        await state.clear()
        return
    await state.set_state(OrderFlow.picking_location)
    await _edit_or_answer(callback, texts.ORDER_PICK_LOCATION, keyboards.locations(locs))


async def _show_volumes(callback: CallbackQuery, state: FSMContext, location_name: str) -> None:
    await state.set_state(OrderFlow.picking_volume)
    await _edit_or_answer(
        callback,
        texts.ORDER_PICK_VOLUME.format(location=escape(location_name)),
        keyboards.volumes(),
    )


async def _show_durations(callback: CallbackQuery, state: FSMContext,
                           location_name: str, volume_gb: int) -> None:
    await state.set_state(OrderFlow.picking_duration)
    await _edit_or_answer(
        callback,
        texts.ORDER_PICK_DURATION.format(
            location=escape(location_name),
            volume=volume_gb,
        ),
        keyboards.durations(),
    )


async def _show_review(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    price = _calc_price_for(db, int(data["volume_gb"]), int(data["duration_days"]))
    await state.update_data(price=price)
    await state.set_state(OrderFlow.reviewing)
    await _edit_or_answer(
        callback,
        texts.ORDER_REVIEW.format(
            location=escape(str(data["location_name"])),
            volume=int(data["volume_gb"]),
            days=int(data["duration_days"]),
            price=texts.format_price(price),
        ),
        keyboards.confirm_order(),
    )


# ---------- entry ----------
@router.callback_query(F.data == keyboards.CB_MAIN_BUY)
async def cb_start_order(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await _show_locations(callback, db, state)
    await callback.answer()


# ---------- pick location ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_location),
    F.data.startswith(keyboards.CB_LOC_PREFIX),
)
async def cb_pick_location(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    loc_id_str = (callback.data or "").removeprefix(keyboards.CB_LOC_PREFIX)
    try:
        loc_id = int(loc_id_str)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None or not loc.enabled:
        await callback.answer("این لوکیشن دیگر در دسترس نیست.", show_alert=True)
        await _show_locations(callback, db, state)
        return

    await state.update_data(
        location_id=loc.id,
        location_name=loc.name,
        inbound_ids=loc.inbound_ids,
    )
    await _show_volumes(callback, state, loc.name)
    await callback.answer()


# ---------- pick volume ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_volume),
    F.data == keyboards.CB_VOL_CUSTOM,
)
async def cb_volume_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OrderFlow.entering_custom_vol)
    await _edit_or_answer(
        callback,
        texts.ORDER_ASK_CUSTOM_VOLUME.format(
            min_gb=texts.CUSTOM_VOLUME_MIN_GB,
            max_gb=texts.CUSTOM_VOLUME_MAX_GB,
        ),
        keyboards.cancel_only(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(OrderFlow.picking_volume),
    F.data.startswith(keyboards.CB_VOL_PREFIX),
)
async def cb_volume_preset(callback: CallbackQuery, state: FSMContext) -> None:
    raw = (callback.data or "").removeprefix(keyboards.CB_VOL_PREFIX)
    if raw == "custom":
        return  # handled by the other callback above
    try:
        gb = int(raw)
    except ValueError:
        await callback.answer()
        return
    if gb not in texts.VOLUME_PRESETS_GB:
        await callback.answer()
        return

    await state.update_data(volume_gb=gb)
    data = await state.get_data()
    await _show_durations(callback, state, str(data["location_name"]), gb)
    await callback.answer()


@router.message(StateFilter(OrderFlow.entering_custom_vol))
async def on_custom_volume(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        gb = int(raw)
    except ValueError:
        await message.answer(
            texts.ORDER_CUSTOM_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            )
        )
        return
    if not (texts.CUSTOM_VOLUME_MIN_GB <= gb <= texts.CUSTOM_VOLUME_MAX_GB):
        await message.answer(
            texts.ORDER_CUSTOM_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            )
        )
        return

    await state.update_data(volume_gb=gb)
    await state.set_state(OrderFlow.picking_duration)
    data = await state.get_data()
    await message.answer(
        texts.ORDER_PICK_DURATION.format(
            location=escape(str(data["location_name"])),
            volume=gb,
        ),
        reply_markup=keyboards.durations(),
    )


# ---------- pick duration ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_duration),
    F.data.startswith(keyboards.CB_DUR_PREFIX),
)
async def cb_pick_duration(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    raw = (callback.data or "").removeprefix(keyboards.CB_DUR_PREFIX)
    try:
        days = int(raw)
    except ValueError:
        await callback.answer()
        return
    if days not in texts.DURATION_PRESETS_DAYS:
        await callback.answer()
        return

    await state.update_data(duration_days=days)
    await _show_review(callback, state, db)
    await callback.answer()


# ---------- review & confirm ----------
@router.callback_query(
    StateFilter(OrderFlow.reviewing),
    F.data == keyboards.CB_ORDER_CONFIRM,
)
async def cb_confirm_order(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()
    user = callback.from_user
    if user is None:
        await callback.answer()
        return

    order_id = db.create_order(
        user_id=user.id,
        location_id=int(data["location_id"]),
        location_name=str(data["location_name"]),
        volume_gb=int(data["volume_gb"]),
        duration_days=int(data["duration_days"]),
        price=int(data["price"]),
    )
    await state.update_data(order_id=order_id)
    await state.set_state(OrderFlow.awaiting_receipt)

    card_number = db.get_setting("card_number", "—") or "—"
    card_holder = db.get_setting("card_holder", "—") or "—"

    await _edit_or_answer(
        callback,
        texts.ORDER_PAYMENT_INSTRUCTIONS.format(
            order_id=order_id,
            price=texts.format_price(int(data["price"])),
            card_number=escape(card_number),
            card_holder=escape(card_holder),
        ),
        keyboards.cancel_only(),
    )
    await callback.answer()


# ---------- back/cancel ----------
@router.callback_query(F.data == keyboards.CB_ORDER_CANCEL)
async def cb_cancel_anywhere(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit_or_answer(callback, texts.CANCELLED, keyboards.main_menu())
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ORDER_BACK_LOC)
async def cb_back_to_locations(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await _show_locations(callback, db, state)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ORDER_BACK_VOL)
async def cb_back_to_volumes(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    loc_name = str(data.get("location_name", "—"))
    await _show_volumes(callback, state, loc_name)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ORDER_BACK_DUR)
async def cb_back_to_duration(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    loc_name = str(data.get("location_name", "—"))
    vol_gb = int(data.get("volume_gb", 0))
    await _show_durations(callback, state, loc_name, vol_gb)
    await callback.answer()


# ---------- receipt photo ----------
@router.message(StateFilter(OrderFlow.awaiting_receipt), F.photo)
async def on_receipt_photo(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    data = await state.get_data()
    order_id = int(data.get("order_id", 0))
    if not order_id or message.photo is None:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())
        return

    # Highest-resolution photo size is last.
    file_id = message.photo[-1].file_id
    db.set_order_screenshot(order_id, file_id, new_status="awaiting_review")

    await state.clear()
    await message.answer(texts.ORDER_RECEIPT_RECEIVED, reply_markup=keyboards.main_menu())

    user = message.from_user
    full_name = "—"
    user_id = 0
    if user is not None:
        full_name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
        user_id = user.id

    caption = texts.NEW_RECEIPT_NOTIFY.format(
        order_id=order_id,
        user_id=user_id,
        full_name=escape(full_name),
        location=escape(str(data["location_name"])),
        volume=int(data["volume_gb"]),
        days=int(data["duration_days"]),
        price=texts.format_price(int(data["price"])),
    )
    review_kb = keyboards.admin_review(order_id=order_id, user_id=user_id)

    for admin_id in settings.admin_ids:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                reply_markup=review_kb,
            )
        except Exception:  # noqa: BLE001 — admin may have blocked the bot
            log.exception("Failed to send receipt to admin %s", admin_id)


@router.message(StateFilter(OrderFlow.awaiting_receipt))
async def on_receipt_non_photo(message: Message) -> None:
    await message.answer(texts.ORDER_RECEIPT_NEED_PHOTO)
