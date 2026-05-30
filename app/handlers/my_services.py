"""User-facing "سرویس‌های من" (My Services) flow.

Lets a buyer:
  * see all their orders (active, pending, disabled, etc.) with status badges
  * view the connection info (sub link + per-inbound configs)
  * view live usage from the 3x-ui panel
  * disable / re-enable a service
  * rename a service (local nickname only)
  * regenerate the configs (disable old client on panel + create a new one
    with the remaining traffic + same expiry — old links stop working)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.db import Database
from app.xui import XuiClient, XuiError, build_client_email


router = Router(name="my_services")
log = logging.getLogger(__name__)

MAX_NICKNAME_LEN = 30


class RenameFlow(StatesGroup):
    waiting_for_nickname = State()


# ---------- helpers ----------
async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup)
            return
        except Exception:  # noqa: BLE001 — uneditable (e.g. photo)
            pass
    if callback.message is not None:
        await callback.message.answer(text, reply_markup=reply_markup)


def _status_badge(status: str) -> str:
    return texts.STATUS_BADGE.get(status, status)


def _format_expiry(ms: int) -> tuple[str, str]:
    """Return (absolute, time_left) strings."""
    if ms <= 0:
        return (texts.VIEW_USAGE_NEVER_EXPIRES, "—")
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    absolute = dt.strftime("%Y-%m-%d %H:%M UTC")
    remaining_seconds = int(ms / 1000 - time.time())
    if remaining_seconds <= 0:
        return (absolute, texts.VIEW_USAGE_EXPIRED)
    days, rem = divmod(remaining_seconds, 86400)
    hours = rem // 3600
    if days > 0:
        time_left = f"{days} روز و {hours} ساعت"
    else:
        minutes = (remaining_seconds % 3600) // 60
        time_left = f"{hours} ساعت و {minutes} دقیقه"
    return (absolute, time_left)


def _service_list_label(row) -> str:
    badge = _status_badge(str(row["status"]))
    nick = f" — «{row['nickname']}»" if (row["nickname"] or "") else ""
    return f"{badge} #{row['id']} · {row['location_name']} · {row['volume_gb']}GB/{row['duration_days']}d{nick}"


def _build_detail_text(row) -> str:
    nickname_part = f" — «{escape(row['nickname'])}»" if (row["nickname"] or "") else ""
    return texts.SERVICE_DETAIL.format(
        order_id=row["id"],
        nickname_part=nickname_part,
        location=escape(str(row["location_name"])),
        volume=int(row["volume_gb"]),
        days=int(row["duration_days"]),
        price=texts.format_price(int(row["price"])),
        status=_status_badge(str(row["status"])),
        created_at=str(row["created_at"]),
    )


def _own_order_or_none(db: Database, order_id: int, user_id: int):
    row = db.get_order(order_id)
    if row is None or int(row["user_id"]) != user_id:
        return None
    return row


# ---------- entry: list ----------
@router.callback_query(F.data == keyboards.CB_MAIN_MY_SERVICES)
@router.callback_query(F.data == keyboards.CB_MY_LIST)
async def cb_my_services(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return

    rows = db.list_user_orders(user.id, limit=50)
    if not rows:
        await _edit_or_answer(callback, texts.MY_SERVICES_EMPTY, keyboards.back_to_menu())
        await callback.answer()
        return

    items = [{"id": int(r["id"]), "label": _service_list_label(r)} for r in rows]
    await _edit_or_answer(
        callback, texts.MY_SERVICES_HEADER, keyboards.my_services_list(items)
    )
    await callback.answer()


# ---------- detail ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_DETAIL_PREFIX))
async def cb_my_service_detail(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_DETAIL_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None:
        await callback.answer("سرویس یافت نشد.", show_alert=True)
        return

    text = _build_detail_text(row)
    provisioned = row["status"] == "provisioned"
    if not provisioned:
        text += texts.SERVICE_NOT_PROVISIONED_ACTIONS

    # We don't know the live enabled state without an API call; assume
    # enabled and let the toggle handler reconcile if needed. Cheap & correct
    # for the common case.
    await _edit_or_answer(
        callback, text,
        keyboards.my_service_detail(order_id, provisioned=provisioned, enabled=True),
    )
    await callback.answer()


# ---------- view configs ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_CONFIGS_PREFIX))
async def cb_view_configs(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_CONFIGS_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    sub_links: list[str] = []
    try:
        sub_links = json.loads(row["sub_links"] or "[]")
    except (TypeError, ValueError):
        sub_links = []

    sub_url = location.render_sub_url(row["xui_sub_id"]) if location else None
    configs_block = texts.format_configs_block(
        sub_url=sub_url, sub_links=[escape(x) for x in sub_links]
    )
    await _edit_or_answer(
        callback,
        texts.VIEW_CONFIGS_TITLE.format(order_id=order_id, configs_block=configs_block),
        keyboards.back_to_service(order_id),
    )
    await callback.answer()


# ---------- view usage ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_USAGE_PREFIX))
async def cb_view_usage(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_USAGE_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    if location is None or not row["xui_email"]:
        await callback.answer("اطلاعات کافی نیست.", show_alert=True)
        return

    await callback.answer("⏳ در حال دریافت اطلاعات از پنل...")
    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            usage = await xui.get_usage(str(row["xui_email"]))
    except XuiError as exc:
        await _edit_or_answer(
            callback,
            texts.VIEW_USAGE_FETCH_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error fetching usage for order %s", order_id)
        await _edit_or_answer(
            callback,
            texts.VIEW_USAGE_FETCH_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return

    total_str = (
        texts.VIEW_USAGE_UNLIMITED_TRAFFIC
        if usage.is_unlimited_traffic
        else texts.format_bytes(usage.total_bytes)
    )
    remaining_str = (
        texts.VIEW_USAGE_UNLIMITED_TRAFFIC
        if usage.is_unlimited_traffic
        else texts.format_bytes(usage.remaining_bytes)
    )
    absolute, time_left = _format_expiry(usage.expiry_time_ms)
    enabled_str = texts.VIEW_USAGE_ENABLED if usage.enable else texts.VIEW_USAGE_DISABLED

    text = texts.VIEW_USAGE_TITLE.format(
        order_id=order_id,
        enabled=enabled_str,
        used=texts.format_bytes(usage.used_bytes),
        total=total_str,
        remaining=remaining_str,
        expiry=absolute,
        time_left=time_left,
    )
    await _edit_or_answer(callback, text, keyboards.back_to_service(order_id))


# ---------- toggle (disable/enable) ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_TOGGLE_PREFIX))
async def cb_toggle(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_TOGGLE_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    if location is None or not row["xui_email"]:
        await callback.answer("اطلاعات کافی نیست.", show_alert=True)
        return

    # We don't store live enable state; fetch first to flip it.
    await callback.answer("⏳ در حال اعمال تغییر...")
    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            usage = await xui.get_usage(str(row["xui_email"]))
            new_state = not usage.enable
            await xui.update_client(email=str(row["xui_email"]), enable=new_state)
    except XuiError as exc:
        await _edit_or_answer(
            callback,
            texts.TOGGLE_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error toggling order %s", order_id)
        await _edit_or_answer(
            callback,
            texts.TOGGLE_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return

    msg = (
        texts.TOGGLE_OK_ENABLED.format(order_id=order_id)
        if new_state
        else texts.TOGGLE_OK_DISABLED.format(order_id=order_id)
    )
    await _edit_or_answer(callback, msg, keyboards.back_to_service(order_id))


# ---------- rename ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_RENAME_PREFIX))
async def cb_rename(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_RENAME_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None:
        await callback.answer("سرویس یافت نشد.", show_alert=True)
        return

    await state.set_state(RenameFlow.waiting_for_nickname)
    await state.update_data(rename_order_id=order_id)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.RENAME_PROMPT.format(order_id=order_id))
    await callback.answer()


@router.message(StateFilter(RenameFlow.waiting_for_nickname), Command("cancel"))
async def cmd_cancel_rename(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())


@router.message(StateFilter(RenameFlow.waiting_for_nickname))
async def on_nickname_received(
    message: Message, state: FSMContext, db: Database
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data.get("rename_order_id", 0))
    if not order_id:
        await state.clear()
        return

    nick = (message.text or "").strip()
    if nick == "-":
        db.set_order_nickname(order_id, None)
        await state.clear()
        await message.answer(texts.RENAME_CLEARED, reply_markup=keyboards.back_to_service(order_id) if False else keyboards.main_menu())
        return

    if len(nick) > MAX_NICKNAME_LEN:
        await message.answer(texts.RENAME_TOO_LONG)
        return

    db.set_order_nickname(order_id, nick or None)
    await state.clear()
    await message.answer(texts.RENAME_OK, reply_markup=keyboards.main_menu())


# ---------- regenerate (destructive) ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_REGEN_PREFIX)
                       & ~F.data.startswith(keyboards.CB_MY_REGEN_CONFIRM_PREFIX))
async def cb_regen_ask(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_REGEN_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return
    if not row["xui_email"]:
        await callback.answer(texts.REGEN_NOT_SUPPORTED, show_alert=True)
        return

    await _edit_or_answer(callback, texts.REGEN_CONFIRM, keyboards.regen_confirm(order_id))
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_MY_REGEN_CONFIRM_PREFIX))
async def cb_regen_confirm(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_REGEN_CONFIRM_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    if location is None or not row["xui_email"]:
        await callback.answer(texts.REGEN_NOT_SUPPORTED, show_alert=True)
        return

    await _edit_or_answer(callback, texts.REGEN_IN_PROGRESS)
    await callback.answer()

    old_email = str(row["xui_email"])
    user_id = int(row["user_id"])

    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            # Fetch remaining quota + expiry from the panel; fall back gracefully.
            try:
                usage = await xui.get_usage(old_email)
                remaining_bytes = (
                    usage.remaining_bytes
                    if not usage.is_unlimited_traffic
                    else int(row["volume_gb"]) * 1024 ** 3
                )
                remaining_gb = max(1, remaining_bytes // (1024 ** 3))
                expiry_ms = (
                    usage.expiry_time_ms
                    if usage.expiry_time_ms > 0
                    else int((time.time() + int(row["duration_days"]) * 86400) * 1000)
                )
            except XuiError:
                # If we can't read usage, regenerate with the original budget.
                remaining_gb = int(row["volume_gb"])
                expiry_ms = int((time.time() + int(row["duration_days"]) * 86400) * 1000)

            # Step 1: disable the old client so its links stop working.
            try:
                await xui.update_client(email=old_email, enable=False)
            except XuiError as exc:
                log.warning("Could not disable old client %s during regen: %s",
                            old_email, exc)

            # Step 2: create a new client with a fresh email.
            #         We append a regen counter so we never clash.
            n_regens = 1
            base_email = build_client_email(user_id, order_id)
            new_email = old_email if old_email == base_email else base_email
            if new_email == old_email:
                # First regen ever for this order; bump suffix
                new_email = f"{base_email}_r{n_regens}"
            while await xui.client_exists(new_email):
                n_regens += 1
                new_email = f"{base_email}_r{n_regens}"

            add_resp = await xui.add_client(
                email=new_email,
                volume_gb=remaining_gb,
                duration_days=1,  # ignored — we overwrite expiryTime via update below
                inbound_ids=location.inbound_ids,
                tg_user_id=user_id,
            )
            # Step 3: align expiry to the original (so user doesn't gain time).
            try:
                await xui.update_client(email=new_email, expiry_time_ms=expiry_ms)
            except XuiError as exc:
                log.warning("Could not align expiry on regen for %s: %s", new_email, exc)

            # Step 4: resolve subId/uuid via list (preferred) + sub links.
            new_sub_id, new_uuid = await xui.resolve_client_identity(
                new_email, add_resp=add_resp
            )
            new_uuid = new_uuid or ""
            new_links = await xui.get_sub_links(new_sub_id) if new_sub_id else []
    except Exception as exc:  # noqa: BLE001 — any failure → tell user, leave DB alone
        log.exception("Regen failed for order %s", order_id)
        await _edit_or_answer(
            callback,
            texts.REGEN_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return

    db.update_order_xui(
        order_id=order_id,
        email=new_email,
        sub_id=new_sub_id,
        client_uuid=new_uuid,
        sub_links=new_links,
    )

    sub_url = location.render_sub_url(new_sub_id)
    configs_block = texts.format_configs_block(
        sub_url=sub_url, sub_links=[escape(x) for x in new_links]
    )
    await _edit_or_answer(
        callback,
        texts.REGEN_OK.format(configs_block=configs_block),
        keyboards.back_to_service(order_id),
    )
