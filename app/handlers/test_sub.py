"""Free one-time test subscription flow (100 MB, hidden test location)."""

from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.db import Database, TEST_VOLUME_BYTES
from app.handlers.buyer_ui import buyer_reply_keyboard, buyer_show_test_button
from app.xui import XuiClient, XuiError, build_client_email


router = Router(name="test_sub")
log = logging.getLogger(__name__)


class TestFlow(StatesGroup):
    confirming = State()


def _test_unavailable_reason(db: Database, user_id: int) -> str | None:
    if not db.is_test_feature_enabled():
        return texts.TEST_SUB_DISABLED
    if db.get_test_location() is None:
        return texts.TEST_SUB_NO_LOCATION
    if db.user_has_claimed_test(user_id):
        return texts.TEST_SUB_ALREADY_USED
    return None


async def _start_test_flow(message: Message, state: FSMContext, db: Database) -> None:
    user = message.from_user
    if user is None:
        return
    await state.clear()
    reason = _test_unavailable_reason(db, user.id)
    if reason:
        await message.answer(
            reason,
            reply_markup=buyer_reply_keyboard(message, db),
        )
        return

    loc = db.get_test_location()
    assert loc is not None
    await state.set_state(TestFlow.confirming)
    await message.answer(
        texts.TEST_SUB_CONFIRM.format(
            location=escape(loc.name),
            volume=texts.format_test_volume(),
            days=texts.TEST_DURATION_DAYS,
        ),
        reply_markup=keyboards.test_sub_confirm(),
    )


@router.message(F.text == texts.BTN_TEST_SUB, StateFilter(None))
async def msg_test_sub(message: Message, state: FSMContext, db: Database) -> None:
    await _start_test_flow(message, state, db)


@router.callback_query(F.data == keyboards.CB_MAIN_TEST, StateFilter(None))
async def cb_test_sub(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _start_test_flow(callback.message, state, db)
    await callback.answer()


@router.callback_query(F.data == "test:confirm", StateFilter(TestFlow.confirming))
async def cb_test_confirm(
    callback: CallbackQuery, state: FSMContext, db: Database
) -> None:
    user = callback.from_user
    if user is None or callback.message is None:
        await callback.answer()
        return

    reason = _test_unavailable_reason(db, user.id)
    if reason:
        await state.clear()
        await callback.message.answer(
            reason,
            reply_markup=buyer_reply_keyboard(callback.message, db),
        )
        await callback.answer()
        return

    loc = db.get_test_location()
    if loc is None or not loc.inbound_ids:
        await callback.answer("لوکیشن تست در دسترس نیست.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(texts.TEST_SUB_PROVISIONING)

    order_id = db.create_order(
        user_id=user.id,
        location_id=loc.id,
        location_name=loc.name,
        volume_gb=0,
        duration_days=texts.TEST_DURATION_DAYS,
        price=0,
        is_test=True,
    )
    email = build_client_email(order_id)

    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            result = await xui.provision(
                email=email,
                volume_gb=1,
                duration_days=texts.TEST_DURATION_DAYS,
                inbound_ids=loc.inbound_ids,
                tg_user_id=user.id,
                total_bytes=TEST_VOLUME_BYTES,
            )
    except XuiError as exc:
        log.warning("Test provision failed for order %s: %s", order_id, exc)
        db.set_order_status(order_id, "failed")
        await callback.message.edit_text(
            texts.TEST_SUB_FAILED.format(error=escape(str(exc)))
        )
        await state.clear()
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected test provision error for order %s", order_id)
        db.set_order_status(order_id, "failed")
        await callback.message.edit_text(
            texts.TEST_SUB_FAILED.format(error=escape(str(exc)))
        )
        await state.clear()
        return

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
    show_test = buyer_show_test_button(db, user.id)
    await callback.message.answer(
        texts.TEST_SUB_OK.format(configs_block=configs_block),
        reply_markup=keyboards.main_reply_keyboard(show_test=show_test),
    )
