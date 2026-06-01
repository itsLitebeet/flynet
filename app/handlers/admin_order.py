"""Admin: /order, /editorder — view and manage provisioned orders."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import ORDERS_MANAGE
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.admin_order_ui import format_admin_order_detail
from app.logs import Actor, make_logger
from app.xui import XuiClient, XuiError

router = Router(name="admin_order")
log = logging.getLogger(__name__)


async def send_admin_order_view(
    message: Message,
    db: Database,
    order_id: int,
    *,
    edit_in_place: bool = False,
    manage_header: bool = False,
    back_data: str | None = keyboards.CB_ADM_PENDING_LIST,
) -> bool:
    """Show order detail + management keyboard; return False if not found."""
    from app.handlers.admin_ui_helpers import admin_edit_or_answer

    text = format_admin_order_detail(db, order_id)
    if text is None:
        return False

    order = db.get_order(order_id)
    assert order is not None
    panel = await _panel_for_order(db, order)
    if manage_header:
        text = texts.ADMIN_EDIT_ORDER_HEADER.format(detail=text)
    markup = keyboards.admin_edit_order_keyboard(
        order_id,
        show_panel_actions=panel is not None,
        show_db_delete=True,
        back_data=back_data,
    )
    await admin_edit_or_answer(
        message, text, markup, edit_in_place=edit_in_place
    )
    return True


async def _panel_for_order(db: Database, order) -> tuple | None:
    """Return (location, email) or None if panel ops impossible."""
    if str(order["status"]) != "provisioned" or not order["xui_email"]:
        return None
    loc = db.get_location(int(order["location_id"]))
    if loc is None:
        return None
    return loc, str(order["xui_email"])


# ---------- /order ----------
@router.message(Command("order"))
async def cmd_order(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_ORDER_USAGE)
        return
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_ORDER_USAGE)
        return

    if not await send_admin_order_view(message, db, order_id):
        await message.answer(texts.ADMIN_ORDER_NOTFOUND)


# ---------- /editorder ----------
@router.message(Command("editorder"))
async def cmd_editorder(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_EDIT_ORDER_USAGE)
        return
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_EDIT_ORDER_USAGE)
        return

    if not await send_admin_order_view(
        message, db, order_id, manage_header=True
    ):
        await message.answer(texts.ADMIN_ORDER_NOTFOUND)


# ---------- panel enable / disable ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_ENABLE_PREFIX))
async def cb_order_enable(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_ENABLE_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    panel = await _panel_for_order(db, order)
    if panel is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return
    loc, email = panel

    await callback.answer("⏳ …")
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            await xui.update_client(email=email, enable=True)
    except XuiError as exc:
        if isinstance(callback.message, Message):
            await callback.message.answer(
                texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
            )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_EDIT_ORDER_ENABLED.format(order_id=order_id)
        )
    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="فعال‌سازی در پنل",
        )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_DISABLE_PREFIX))
async def cb_order_disable(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_DISABLE_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    panel = await _panel_for_order(db, order)
    if panel is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return
    loc, email = panel

    await callback.answer("⏳ …")
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            await xui.update_client(email=email, enable=False)
    except XuiError as exc:
        if isinstance(callback.message, Message):
            await callback.message.answer(
                texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
            )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_EDIT_ORDER_DISABLED.format(order_id=order_id)
        )
    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="غیرفعال در پنل",
        )


# ---------- delete (confirm) — register OK before ASK; prefixes must not nest ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_DELETE_OK_PREFIX))
async def cb_order_delete_ok(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_DELETE_OK_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    await callback.answer("⏳ …")

    panel_err: str | None = None
    panel = await _panel_for_order(db, order)
    if panel is not None:
        loc, email = panel
        try:
            async with XuiClient(loc.base_url, loc.api_token) as xui:
                await xui.delete_client(email, keep_traffic=1)
        except XuiError as exc:
            panel_err = str(exc)
            log.warning("Panel delete failed for order %s: %s", order_id, exc)

    if not db.delete_order(order_id):
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "❗ حذف از دیتابیس ناموفق.",
                reply_markup=None,
            )
        return

    if isinstance(callback.message, Message):
        if panel_err:
            await callback.message.edit_text(
                texts.ADMIN_ORDER_DELETED_PARTIAL.format(
                    order_id=order_id, error=escape(panel_err)
                ),
                reply_markup=None,
            )
        else:
            await callback.message.edit_text(
                texts.ADMIN_ORDER_DELETED_OK.format(order_id=order_id),
                reply_markup=None,
            )

    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="حذف از پنل و ربات",
        )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_DELETE_ASK_PREFIX))
async def cb_order_delete_ask(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_DELETE_ASK_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_ORDER_DELETE_CONFIRM.format(order_id=order_id),
            reply_markup=keyboards.admin_order_delete_confirm(order_id),
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_ORDER_DELETE_CANCEL)
async def cb_order_delete_cancel(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.ADMIN_ORDER_DELETE_CANCELLED, reply_markup=None)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_MANAGE_PREFIX))
async def cb_order_manage(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_MANAGE_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    if not await send_admin_order_view(
        callback.message,
        db,
        order_id,
        edit_in_place=True,
        manage_header=True,
    ):
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    await callback.answer()


def _parse_order_id(data: str | None, prefix: str) -> int | None:
    try:
        return int((data or "").removeprefix(prefix))
    except ValueError:
        return None
