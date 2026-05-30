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
from app.config import Settings
from app.db import Database
from app.xui import XuiClient, XuiError, build_client_email


router = Router(name="review")
log = logging.getLogger(__name__)


class DeclineFlow(StatesGroup):
    waiting_reason = State()


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def _format_sub_links(links: list[str]) -> str:
    if not links:
        return "—"
    return "\n".join(f"<code>{escape(link)}</code>" for link in links)


# ---------- Accept ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_ACCEPT_PREFIX))
async def cb_accept_order(
    callback: CallbackQuery,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    if callback.from_user is None or not _is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADMIN_ACCEPT_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return
    if order["status"] != "awaiting_review":
        await callback.answer(texts.REVIEW_ALREADY, show_alert=True)
        return

    # Optimistically mark as approved so a second admin click is a no-op.
    db.set_order_status(order_id, "approved", admin_id=callback.from_user.id)
    await callback.answer(texts.REVIEW_ACCEPTED)
    # Strip buttons from the receipt message so it doesn't get re-clicked.
    try:
        if isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass

    location = db.get_location(int(order["location_id"]))
    if location is None or not location.inbound_ids:
        err = "لوکیشن مرتبط با این سفارش حذف شده یا inbound ندارد."
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
        await bot.send_message(callback.from_user.id, texts.REVIEW_PROVISION_ERR.format(error=err))
        await bot.send_message(int(order["user_id"]), texts.ORDER_PROVISION_FAILED_USER)
        return

    email = build_client_email(int(order["user_id"]), order_id)

    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            result = await xui.provision(
                email=email,
                volume_gb=int(order["volume_gb"]),
                duration_days=int(order["duration_days"]),
                inbound_ids=location.inbound_ids,
                tg_user_id=int(order["user_id"]),
            )
    except XuiError as exc:
        log.warning("Provisioning failed for order %s: %s", order_id, exc)
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
        await bot.send_message(
            callback.from_user.id,
            texts.REVIEW_PROVISION_ERR.format(error=escape(str(exc))),
        )
        await bot.send_message(int(order["user_id"]), texts.ORDER_PROVISION_FAILED_USER)
        return
    except Exception as exc:  # noqa: BLE001 — any other failure (network, etc.)
        log.exception("Unexpected provisioning error for order %s", order_id)
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
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

    try:
        await bot.send_message(
            int(order["user_id"]),
            texts.ORDER_PROVISIONED_NOTIFY.format(
                order_id=order_id,
                location=escape(str(order["location_name"])),
                volume=int(order["volume_gb"]),
                days=int(order["duration_days"]),
                links=_format_sub_links(result.sub_links),
            ),
        )
    except Exception:  # noqa: BLE001 — user may have blocked the bot
        log.exception("Failed to notify user %s about provisioned order %s",
                      order["user_id"], order_id)

    await bot.send_message(callback.from_user.id, texts.REVIEW_PROVISION_OK)


# ---------- Decline ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_DECLINE_PREFIX))
async def cb_decline_order(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if callback.from_user is None or not _is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADMIN_DECLINE_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return
    if order["status"] != "awaiting_review":
        await callback.answer(texts.REVIEW_ALREADY, show_alert=True)
        return

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
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        # Ignore non-admin messages that somehow land here.
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
    if order is None or order["status"] != "awaiting_review":
        await message.answer(texts.REVIEW_ALREADY)
        return

    db.set_order_status(
        order_id, "declined",
        admin_id=message.from_user.id,
        decline_reason=reason,
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
