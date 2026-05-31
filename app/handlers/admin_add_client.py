"""Admin wizard: manually provision a client (buttons + numeric input)."""

from __future__ import annotations

import logging
import time
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import ORDERS_MANAGE
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.admin_ui_helpers import admin_edit_or_answer
from app.logs import Actor, make_logger
from app.xui import XuiClient, XuiError, build_client_email

router = Router(name="admin_add_client")
log = logging.getLogger(__name__)

_DAYS_MIN = 1
_DAYS_MAX = 3650
_SKIP_USER_TEXT = frozenset({"-", "—", "skip", "none"})


class AdminAddClientFlow(StatesGroup):
    waiting_user_id = State()
    waiting_volume = State()
    waiting_days = State()
    picking_location = State()


def _calc_order_price(
    db: Database, volume_gb: int, duration_days: int, location_id: int
) -> int:
    base, per_gb, per_day = db.get_pricing_for_location(location_id)
    base_price = texts.calc_price(volume_gb, duration_days, base, per_gb, per_day)
    return db.resolve_price(base_price)


def _parse_positive_int(raw: str) -> int | None:
    s = (raw or "").strip()
    if not s.isdigit():
        return None
    value = int(s)
    return value if value > 0 else None


async def _prompt_volume(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminAddClientFlow.waiting_volume)
    await message.answer(
        texts.ADMIN_ADD_CLIENT_VOLUME_PROMPT.format(
            min_gb=texts.CUSTOM_VOLUME_MIN_GB,
            max_gb=texts.CUSTOM_VOLUME_MAX_GB,
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_HOME
        ),
    )


async def _start_add_client(
    message: Message, state: FSMContext, db: Database
) -> None:
    await state.clear()
    await state.set_state(AdminAddClientFlow.waiting_user_id)
    await message.answer(
        texts.ADMIN_ADD_CLIENT_USER_PROMPT,
        reply_markup=keyboards.admin_add_client_user_keyboard(),
    )


@router.callback_query(F.data == keyboards.CB_ADM_ADD_CLIENT)
async def cb_admin_add_client_start(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await _start_add_client(callback.message, state, db)
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminAddClientFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(AdminAddClientFlow)
)
async def add_client_flow_cancel(
    event: Message | CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)


@router.callback_query(
    F.data == keyboards.CB_ADM_ADD_CLIENT_SKIP_USER,
    StateFilter(AdminAddClientFlow.waiting_user_id),
)
async def add_client_skip_user(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.update_data(target_user_id=None)
    await _prompt_volume(callback.message, state)
    await callback.answer()


@router.message(StateFilter(AdminAddClientFlow.waiting_user_id))
async def add_client_user_id(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        await state.clear()
        return

    raw = (message.text or "").strip()
    if raw.lower() in _SKIP_USER_TEXT:
        await state.update_data(target_user_id=None)
        await _prompt_volume(message, state)
        return

    user_id = _parse_positive_int(raw)
    if user_id is None:
        await message.answer(texts.ADMIN_ADD_CLIENT_USER_INVALID)
        return

    db.upsert_user(user_id=user_id, username=None, first_name=None, last_name=None)
    await state.update_data(target_user_id=user_id)
    await _prompt_volume(message, state)


@router.message(StateFilter(AdminAddClientFlow.waiting_volume))
async def add_client_volume(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        await state.clear()
        return

    gb = _parse_positive_int(message.text or "")
    if gb is None or not (
        texts.CUSTOM_VOLUME_MIN_GB <= gb <= texts.CUSTOM_VOLUME_MAX_GB
    ):
        await message.answer(
            texts.ADMIN_ADD_CLIENT_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            )
        )
        return

    await state.update_data(volume_gb=gb)
    await state.set_state(AdminAddClientFlow.waiting_days)
    await message.answer(
        texts.ADMIN_ADD_CLIENT_DAYS_PROMPT,
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_HOME
        ),
    )


@router.message(StateFilter(AdminAddClientFlow.waiting_days))
async def add_client_days(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        await state.clear()
        return

    days = _parse_positive_int(message.text or "")
    if days is None or not (_DAYS_MIN <= days <= _DAYS_MAX):
        await message.answer(
            texts.ADMIN_ADD_CLIENT_DAYS_INVALID.format(
                min_days=_DAYS_MIN, max_days=_DAYS_MAX
            )
        )
        return

    locs = db.list_locations(only_enabled=True, exclude_test=True)
    if not locs:
        await state.clear()
        await message.answer(texts.ADMIN_ADD_CLIENT_NO_LOCATIONS)
        return

    await state.update_data(duration_days=days)
    await state.set_state(AdminAddClientFlow.picking_location)
    await message.answer(
        texts.ADMIN_ADD_CLIENT_LOCATION_PROMPT,
        reply_markup=keyboards.admin_add_client_locations(locs),
    )


@router.callback_query(
    StateFilter(AdminAddClientFlow.picking_location),
    F.data.startswith(keyboards.CB_ADM_ADD_CLIENT_LOC_PREFIX),
)
async def add_client_pick_location(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(
        keyboards.CB_ADM_ADD_CLIENT_LOC_PREFIX
    )
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None or not loc.enabled or loc.is_test:
        await callback.answer("لوکیشن در دسترس نیست.", show_alert=True)
        return

    data = await state.get_data()
    try:
        volume_gb = int(data["volume_gb"])
        duration_days = int(data["duration_days"])
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await callback.answer("اطلاعات ناقص است. دوباره شروع کنید.", show_alert=True)
        return

    target_user_id = data.get("target_user_id")
    if target_user_id is not None:
        try:
            target_user_id = int(target_user_id)
        except (TypeError, ValueError):
            target_user_id = None

    if not loc.inbound_ids:
        await callback.answer("inbound برای این لوکیشن تنظیم نشده.", show_alert=True)
        return

    await callback.answer()
    await admin_edit_or_answer(
        callback.message,
        texts.ADMIN_ADD_CLIENT_PROVISIONING,
        edit_in_place=True,
    )

    admin_id = callback.from_user.id
    order_id: int | None = None
    if target_user_id is not None:
        price = _calc_order_price(db, volume_gb, duration_days, loc.id)
        order_id = db.create_order(
            user_id=target_user_id,
            location_id=loc.id,
            location_name=loc.name,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
        )
        panel_email = build_client_email(order_id, is_test=False)
        tg_user_id = target_user_id
    else:
        panel_email = f"adm-{admin_id}-{int(time.time())}"
        tg_user_id = admin_id

    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            result = await xui.provision(
                email=panel_email,
                volume_gb=volume_gb,
                duration_days=duration_days,
                inbound_ids=loc.inbound_ids,
                tg_user_id=tg_user_id,
            )
    except XuiError as exc:
        log.warning(
            "Admin manual provision failed%s: %s",
            f" order {order_id}" if order_id else "",
            exc,
        )
        if order_id is not None:
            db.set_order_status(order_id, "failed", admin_id=admin_id)
        await state.clear()
        order_hint = (
            f" (سفارش <code>#{order_id}</code>)" if order_id is not None else ""
        )
        await callback.message.answer(
            texts.ADMIN_ADD_CLIENT_FAILED.format(
                order_hint=order_hint, error=escape(str(exc))
            )
        )
        return
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "Unexpected admin manual provision%s",
            f" order {order_id}" if order_id else "",
        )
        if order_id is not None:
            db.set_order_status(order_id, "failed", admin_id=admin_id)
        await state.clear()
        order_hint = (
            f" (سفارش <code>#{order_id}</code>)" if order_id is not None else ""
        )
        await callback.message.answer(
            texts.ADMIN_ADD_CLIENT_FAILED.format(
                order_hint=order_hint, error=escape(str(exc))
            )
        )
        return

    if order_id is not None:
        db.set_order_provisioned(
            order_id=order_id,
            email=result.email,
            sub_id=result.sub_id,
            client_uuid=result.client_uuid,
            sub_links=result.sub_links,
        )
    await state.clear()

    sub_url = loc.render_sub_url(result.sub_id)
    configs_block = texts.format_configs_block(
        sub_url=sub_url,
        sub_links=[escape(x) for x in result.sub_links],
    )

    if order_id is not None and target_user_id is not None:
        await callback.message.answer(
            texts.ADMIN_ADD_CLIENT_OK.format(
                order_id=order_id,
                user_id=target_user_id,
                location=escape(loc.name),
                volume=volume_gb,
                days=duration_days,
                panel_email=escape(result.email),
                configs_block=configs_block,
            ),
            reply_markup=keyboards.admin_add_client_done_keyboard(),
        )
        try:
            await bot.send_message(
                target_user_id,
                texts.ADMIN_ADD_CLIENT_USER_NOTIFY.format(
                    order_id=order_id,
                    location=escape(loc.name),
                    volume=volume_gb,
                    days=duration_days,
                    configs_block=configs_block,
                ),
            )
        except Exception:  # noqa: BLE001
            log.debug(
                "Could not notify user %s about manual provision", target_user_id
            )
    else:
        await callback.message.answer(
            texts.ADMIN_ADD_CLIENT_OK_PANEL_ONLY.format(
                location=escape(loc.name),
                volume=volume_gb,
                days=duration_days,
                panel_email=escape(result.email),
                configs_block=configs_block,
            ),
            reply_markup=keyboards.admin_add_client_done_keyboard(),
        )

    admin = Actor.from_user(callback.from_user)
    if admin is not None and order_id is not None:
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="ساخت دستی کلاینت",
        )
