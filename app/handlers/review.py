"""Admin payment-review flow.

When an admin clicks Accept on a payment receipt:
  1) We re-check the order is still 'awaiting_review'.
  2) Look up the associated Location's panel credentials.
  3) Call XuiClient.provision() to create the client and fetch sub links.
  4) Notify the user with the links, save the result in the order row.

Decline flow uses a small FSM to collect a reason from the admin and
forwards it to the user.
"""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import ORDERS_REVIEW
from app.config import Settings
from app.db import TEST_VOLUME_BYTES, Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.review_notify import clear_admin_receipt_buttons
from app.logs import Actor, make_logger
from app.xui import XuiClient, XuiError, build_client_email


router = Router(name="review")
log = logging.getLogger(__name__)


class DeclineFlow(StatesGroup):
    waiting_reason = State()


def _status_label(status: str) -> str:
    return texts.STATUS_BADGE.get(status, status)


async def _reject_if_not_reviewable(
    callback: CallbackQuery, db: Database, order_id: int
) -> bool:
    """Return True if order is still awaiting_review; else alert and return False."""
    order = db.get_order(order_id)
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return False
    if order["status"] != "awaiting_review":
        await callback.answer(
            texts.REVIEW_ALREADY.format(status=_status_label(order["status"])),
            show_alert=True,
        )
        return False
    return True




# ---------- Accept ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_ACCEPT_PREFIX))
async def cb_accept_order(
    callback: CallbackQuery,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_REVIEW):
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADMIN_ACCEPT_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    if not await _reject_if_not_reviewable(callback, db, order_id):
        return

    order = db.get_order(order_id)
    assert order is not None
    admin_id = callback.from_user.id
    is_test = bool(order["is_test"]) if "is_test" in order.keys() else False

    if not db.claim_order_review(order_id, "approved", admin_id):
        order = db.get_order(order_id)
        st = order["status"] if order else "—"
        await callback.answer(
            texts.REVIEW_ALREADY.format(status=_status_label(str(st))),
            show_alert=True,
        )
        return

    await callback.answer(texts.REVIEW_ACCEPTED)
    await clear_admin_receipt_buttons(
        bot,
        db,
        order_id,
        acting_admin_id=admin_id,
        action="تأیید شد",
    )

    location = db.get_location(int(order["location_id"]))
    if location is None or not location.inbound_ids:
        err = "لوکیشن مرتبط با این سفارش حذف شده یا inbound ندارد."
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
        admin = Actor.from_user(callback.from_user)
        if admin is not None:
            await make_logger(bot, db).log_order_provision_failed(
                order_id=order_id,
                admin=admin,
                buyer_id=int(order["user_id"]),
                location=str(order["location_name"]),
                volume_gb=int(order["volume_gb"]),
                duration_days=int(order["duration_days"]),
                price=int(order["price"]),
                error=err,
                is_test=is_test,
            )
        await bot.send_message(callback.from_user.id, texts.REVIEW_PROVISION_ERR.format(error=err))
        await bot.send_message(int(order["user_id"]), texts.ORDER_PROVISION_FAILED_USER)
        return

    email = build_client_email(order_id, is_test=is_test)

    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            result = await xui.provision(
                email=email,
                volume_gb=int(order["volume_gb"]),
                duration_days=int(order["duration_days"]),
                inbound_ids=location.inbound_ids,
                tg_user_id=int(order["user_id"]),
                total_bytes=TEST_VOLUME_BYTES if is_test else None,
            )
    except XuiError as exc:
        log.warning("Provisioning failed for order %s: %s", order_id, exc)
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
        admin = Actor.from_user(callback.from_user)
        if admin is not None:
            await make_logger(bot, db).log_order_provision_failed(
                order_id=order_id,
                admin=admin,
                buyer_id=int(order["user_id"]),
                location=str(order["location_name"]),
                volume_gb=int(order["volume_gb"]),
                duration_days=int(order["duration_days"]),
                price=int(order["price"]),
                error=str(exc),
                is_test=is_test,
            )
        await bot.send_message(
            callback.from_user.id,
            texts.REVIEW_PROVISION_ERR.format(error=escape(str(exc))),
        )
        await bot.send_message(int(order["user_id"]), texts.ORDER_PROVISION_FAILED_USER)
        return
    except Exception as exc:  # noqa: BLE001 — any other failure (network, etc.)
        log.exception("Unexpected provisioning error for order %s", order_id)
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
        admin = Actor.from_user(callback.from_user)
        if admin is not None:
            await make_logger(bot, db).log_order_provision_failed(
                order_id=order_id,
                admin=admin,
                buyer_id=int(order["user_id"]),
                location=str(order["location_name"]),
                volume_gb=int(order["volume_gb"]),
                duration_days=int(order["duration_days"]),
                price=int(order["price"]),
                error=str(exc),
                is_test=is_test,
            )
        await bot.send_message(
            callback.from_user.id,
            texts.REVIEW_PROVISION_ERR.format(error=escape(str(exc))),
        )
        await bot.send_message(int(order["user_id"]), texts.ORDER_PROVISION_FAILED_USER)
        return

    db.set_order_provisioned(
        order_id=order_id,
        email=result.email,
        sub_id=result.sub_id,
        client_uuid=result.client_uuid,
        sub_links=result.sub_links,
    )

    sub_url = location.render_sub_url(result.sub_id)
    configs_block = texts.format_configs_block(
        sub_url=sub_url,
        sub_links=[escape(x) for x in result.sub_links],
    )

    try:
        await bot.send_message(
            int(order["user_id"]),
            texts.ORDER_PROVISIONED_NOTIFY.format(
                order_id=order_id,
                location=escape(str(order["location_name"])),
                volume=int(order["volume_gb"]),
                days=int(order["duration_days"]),
                configs_block=configs_block,
            ),
        )
    except Exception:  # noqa: BLE001 — user may have blocked the bot
        log.exception("Failed to notify user %s about provisioned order %s",
                      order["user_id"], order_id)

    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_order_accepted(
            order_id=order_id,
            admin=admin,
            buyer_id=int(order["user_id"]),
            location=str(order["location_name"]),
            volume_gb=int(order["volume_gb"]),
            duration_days=int(order["duration_days"]),
            price=int(order["price"]),
            panel_email=result.email,
            is_test=is_test,
        )

    await bot.send_message(callback.from_user.id, texts.REVIEW_PROVISION_OK)


# ---------- Decline ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_DECLINE_PREFIX))
async def cb_decline_order(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_REVIEW):
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADMIN_DECLINE_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    if not await _reject_if_not_reviewable(callback, db, order_id):
        return

    order = db.get_order(order_id)
    assert order is not None

    await state.set_state(DeclineFlow.waiting_reason)
    await state.update_data(decline_order_id=order_id, decline_user_id=int(order["user_id"]))
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.REVIEW_DECLINE_PROMPT)
    await callback.answer()


@router.message(StateFilter(DeclineFlow.waiting_reason), Command("cancel"))
async def cmd_cancel_decline(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED)


@router.message(StateFilter(DeclineFlow.waiting_reason))
async def on_decline_reason(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_REVIEW):
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data.get("decline_order_id", 0))
    user_id  = int(data.get("decline_user_id", 0))
    reason = (message.text or "").strip() or texts.ORDER_DECLINED_DEFAULT_REASON
    await state.clear()

    if not order_id:
        return

    order = db.get_order(order_id)
    if order is None:
        await message.answer("سفارش پیدا نشد.")
        return
    if order["status"] != "awaiting_review":
        await message.answer(
            texts.REVIEW_ALREADY.format(status=_status_label(order["status"]))
        )
        return

    admin_id = message.from_user.id
    if not db.claim_order_review(
        order_id, "declined", admin_id, decline_reason=reason
    ):
        order = db.get_order(order_id)
        st = order["status"] if order else "—"
        await message.answer(
            texts.REVIEW_ALREADY.format(status=_status_label(str(st)))
        )
        return

    await clear_admin_receipt_buttons(
        bot,
        db,
        order_id,
        acting_admin_id=admin_id,
        action="رد شد",
    )
    is_test = bool(order["is_test"]) if "is_test" in order.keys() else False
    admin = Actor.from_user(message.from_user)
    if admin is not None:
        await make_logger(bot, db).log_order_declined(
            order_id=order_id,
            admin=admin,
            buyer_id=user_id,
            location=str(order["location_name"]),
            volume_gb=int(order["volume_gb"]),
            duration_days=int(order["duration_days"]),
            price=int(order["price"]),
            reason=reason,
            is_test=is_test,
        )
    await message.answer(texts.REVIEW_DECLINE_SENT)

    try:
        await bot.send_message(
            user_id,
            texts.ORDER_DECLINED_NOTIFY.format(
                order_id=order_id,
                reason=escape(reason),
            ),
        )
    except Exception:  # noqa: BLE001
        log.exception("Failed to notify user %s about declined order %s",
                      user_id, order_id)
