"""Admin panel: reply keyboard + inline dashboards (Persian UI)."""

from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import (
    admin_from_message,
    format_base_plans_text,
    format_settings_text,
    format_stats_text,
    is_admin,
    location_pricing_label,
    run_clear_declined,
    run_sync_panel,
)
from app.handlers.admin_users_ui import format_user_detail, format_users_page

router = Router(name="admin_panel")


async def send_admin_home(message: Message, db: Database) -> None:
    await message.answer(
        texts.ADMIN_PANEL_HOME,
        reply_markup=keyboards.admin_reply_keyboard(),
    )
    await message.answer(
        format_stats_text(db),
        reply_markup=keyboards.admin_home_inline(),
    )


async def send_dashboard(message: Message, db: Database) -> None:
    body = texts.ADMIN_DASHBOARD_HEADER.format(stats=format_stats_text(db))
    await message.answer(body, reply_markup=keyboards.admin_dashboard_inline())


async def send_pending_list(message: Message, db: Database) -> None:
    rows = db.pending_orders(limit=20)
    if not rows:
        await message.answer(
            texts.ADMIN_PENDING_EMPTY,
            reply_markup=keyboards.admin_home_inline(),
        )
        return

    buttons: list[dict] = []
    for r in rows:
        buttons.append({
            "id": r["id"],
            "label": texts.ADMIN_PENDING_BTN.format(
                id=r["id"],
                price=texts.format_price(int(r["price"])),
                user_id=r["user_id"],
            ),
        })
    await message.answer(
        texts.ADMIN_PENDING_HEADER.format(count=len(rows)),
        reply_markup=keyboards.admin_pending_list(buttons),
    )


async def send_settings(message: Message, db: Database) -> None:
    await message.answer(
        texts.ADMIN_SETTINGS_MENU + "\n\n" + format_settings_text(db),
        reply_markup=keyboards.admin_settings_inline(),
    )


async def send_base_plans(message: Message, db: Database) -> None:
    await message.answer(
        format_base_plans_text(db),
        reply_markup=keyboards.admin_plans_keyboard(
            db.get_volume_presets(),
            db.get_duration_presets(),
        ),
    )


async def send_tools(message: Message) -> None:
    await message.answer(
        texts.ADMIN_TOOLS_MENU,
        reply_markup=keyboards.admin_tools_inline(),
    )


async def send_locations(message: Message, db: Database) -> None:
    locs = db.list_locations(only_enabled=False)
    if not locs:
        await message.answer(
            texts.ADMIN_LOC_EMPTY,
            reply_markup=keyboards.admin_home_inline(),
        )
        return
    await message.answer(
        texts.ADMIN_LOCATIONS_MENU.format(count=len(locs)),
        reply_markup=keyboards.admin_locations_list(locs),
    )


async def send_users(
    message: Message,
    db: Database,
    page: int = 0,
    *,
    edit_in_place: bool = False,
) -> None:
    text, total_pages, users = format_users_page(db, page)
    if not users:
        markup = keyboards.admin_home_inline()
        if edit_in_place:
            try:
                await message.edit_text(
                    text, reply_markup=markup, parse_mode=ParseMode.HTML
                )
            except Exception:  # noqa: BLE001
                await message.answer(
                    text, reply_markup=markup, parse_mode=ParseMode.HTML
                )
        else:
            await message.answer(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        return

    markup = keyboards.admin_users_keyboard(
        users, page=page, total_pages=total_pages
    )
    if edit_in_place:
        try:
            await message.edit_text(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        except Exception:  # noqa: BLE001
            await message.answer(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
    else:
        await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


async def send_user_detail(
    message: Message,
    db: Database,
    user_id: int,
    *,
    edit_in_place: bool = False,
) -> bool:
    row = db.get_user(user_id)
    text = format_user_detail(db, user_id)
    if text is None or row is None:
        return False
    is_banned = bool(row["is_banned"])
    markup = keyboards.admin_user_detail_keyboard(user_id, is_banned=is_banned)
    if edit_in_place:
        try:
            await message.edit_text(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        except Exception:  # noqa: BLE001
            await message.answer(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
    else:
        await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    return True


def _order_receipt_caption(db: Database, order) -> str | None:
    if order is None or order["status"] != "awaiting_review":
        return None
    loc = db.get_location(int(order["location_id"]))
    loc_name = loc.name if loc else "—"
    user_row = db.get_user(int(order["user_id"]))
    if user_row:
        full_name = escape(
            " ".join(
                p
                for p in [user_row["first_name"], user_row["last_name"]]
                if p
            )
            or "—"
        )
    else:
        full_name = "—"
    return texts.NEW_RECEIPT_NOTIFY.format(
        order_id=order["id"],
        user_id=order["user_id"],
        full_name=full_name,
        location=escape(loc_name),
        volume=int(order["volume_gb"]),
        days=int(order["duration_days"]),
        price=texts.format_price(int(order["price"])),
    )


# ---------- /admin opens panel ----------
@router.message(Command("admin"))
async def cmd_admin_panel(message: Message, settings: Settings, db: Database) -> None:
    if not admin_from_message(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await send_admin_home(message, db)


# ---------- reply keyboard ----------
@router.message(F.text.in_(keyboards.ADMIN_MENU_BUTTONS), StateFilter(None))
async def admin_menu_buttons(
    message: Message, settings: Settings, db: Database
) -> None:
    if not admin_from_message(message, settings):
        return

    text = message.text or ""
    if text == texts.ADMIN_BTN_PANEL:
        await send_admin_home(message, db)
    elif text == texts.ADMIN_BTN_DASHBOARD:
        await send_dashboard(message, db)
    elif text == texts.ADMIN_BTN_PENDING:
        await send_pending_list(message, db)
    elif text == texts.ADMIN_BTN_SETTINGS:
        await send_settings(message, db)
    elif text == texts.ADMIN_BTN_LOCATIONS:
        await send_locations(message, db)
    elif text == texts.ADMIN_BTN_TOOLS:
        await send_tools(message)
    elif text == texts.ADMIN_BTN_USERS:
        await send_users(message, db, page=0)


# ---------- inline navigation ----------
@router.callback_query(F.data == keyboards.CB_ADM_HOME)
async def cb_admin_home(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_PANEL_HOME,
            reply_markup=keyboards.admin_reply_keyboard(),
        )
        await callback.message.answer(
            format_stats_text(db),
            reply_markup=keyboards.admin_home_inline(),
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_DASH)
async def cb_admin_dash(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        body = texts.ADMIN_DASHBOARD_HEADER.format(stats=format_stats_text(db))
        try:
            await callback.message.edit_text(
                body, reply_markup=keyboards.admin_dashboard_inline()
            )
        except Exception:  # noqa: BLE001
            await callback.message.answer(
                body, reply_markup=keyboards.admin_dashboard_inline()
            )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_PENDING_LIST)
async def cb_admin_pending(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_pending_list(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_SETTINGS)
async def cb_admin_settings(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_settings(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_PLANS)
async def cb_admin_plans(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        text = format_base_plans_text(db)
        markup = keyboards.admin_plans_keyboard(
            db.get_volume_presets(),
            db.get_duration_presets(),
        )
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:  # noqa: BLE001
            await send_base_plans(callback.message, db)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_VOL_DEL_PREFIX))
async def cb_admin_del_volume(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_VOL_DEL_PREFIX)
    try:
        gb = int(raw)
    except ValueError:
        await callback.answer()
        return
    ok, reason = db.remove_volume_preset(gb)
    if not ok:
        msg = {
            "missing": texts.ADMIN_PLAN_NOT_FOUND,
            "last": texts.ADMIN_PLAN_LAST,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await callback.answer(msg, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_base_plans_text(db),
            reply_markup=keyboards.admin_plans_keyboard(
                db.get_volume_presets(),
                db.get_duration_presets(),
            ),
        )
    await callback.answer(texts.ADMIN_PLAN_VOL_REMOVED.format(gb=gb))


@router.callback_query(F.data.startswith(keyboards.CB_ADM_DUR_DEL_PREFIX))
async def cb_admin_del_duration(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_DUR_DEL_PREFIX)
    try:
        days = int(raw)
    except ValueError:
        await callback.answer()
        return
    ok, reason = db.remove_duration_preset(days)
    if not ok:
        msg = {
            "missing": texts.ADMIN_PLAN_NOT_FOUND,
            "last": texts.ADMIN_PLAN_LAST,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await callback.answer(msg, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_base_plans_text(db),
            reply_markup=keyboards.admin_plans_keyboard(
                db.get_volume_presets(),
                db.get_duration_presets(),
            ),
        )
    await callback.answer(texts.ADMIN_PLAN_DUR_REMOVED.format(days=days))


@router.callback_query(F.data == keyboards.CB_ADM_TOOLS)
async def cb_admin_tools(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_tools(callback.message)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_LOCATIONS_LIST)
async def cb_admin_locations(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_locations(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_USERS)
async def cb_admin_users(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_users(callback.message, db, page=0, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USERS_PAGE_PREFIX))
async def cb_admin_users_page(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_USERS_PAGE_PREFIX)
    try:
        page = int(raw)
    except ValueError:
        await callback.answer()
        return
    if isinstance(callback.message, Message):
        await send_users(callback.message, db, page=page, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_DETAIL_PREFIX))
async def cb_admin_user_detail(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_USER_DETAIL_PREFIX)
    try:
        user_id = int(raw)
    except ValueError:
        await callback.answer()
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    if not await send_user_detail(
        callback.message, db, user_id, edit_in_place=True
    ):
        await callback.answer("کاربر یافت نشد.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_CMD_HELP)
async def cb_admin_cmd_help(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.ADMIN_HELP)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_BAN_PREFIX))
async def cb_admin_ban_user(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    try:
        user_id = int(
            (callback.data or "").removeprefix(keyboards.CB_ADM_USER_BAN_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return
    if user_id == callback.from_user.id:
        await callback.answer(texts.BAN_SELF, show_alert=True)
        return
    if db.get_user(user_id) is None:
        await callback.answer(texts.BAN_USER_NOTFOUND, show_alert=True)
        return
    db.set_user_banned(user_id, True)
    if isinstance(callback.message, Message):
        await send_user_detail(
            callback.message, db, user_id, edit_in_place=True
        )
    await callback.answer(texts.BAN_OK.format(user_id=user_id))
    await _log_ban_from_callback(bot, db, callback, user_id, banned=True)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_UNBAN_PREFIX))
async def cb_admin_unban_user(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    try:
        user_id = int(
            (callback.data or "").removeprefix(keyboards.CB_ADM_USER_UNBAN_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return
    if db.get_user(user_id) is None:
        await callback.answer(texts.BAN_USER_NOTFOUND, show_alert=True)
        return
    db.set_user_banned(user_id, False)
    if isinstance(callback.message, Message):
        await send_user_detail(
            callback.message, db, user_id, edit_in_place=True
        )
    await callback.answer(texts.UNBAN_OK.format(user_id=user_id))
    await _log_ban_from_callback(bot, db, callback, user_id, banned=False)


async def _log_ban_from_callback(
    bot: Bot, db: Database, callback: CallbackQuery, user_id: int, *, banned: bool
) -> None:
    from app.logs import Actor, make_logger

    admin = Actor.from_user(callback.from_user)
    row = db.get_user(user_id)
    if admin is None or row is None:
        return
    target = Actor(
        user_id=user_id,
        full_name=" ".join(
            p for p in [row["first_name"], row["last_name"]] if p
        )
        or "—",
        username=row["username"],
    )
    await make_logger(bot, db).log_user_ban(
        admin=admin, user=target, banned=banned
    )


# ---------- pending order → resend receipt ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_VIEW_PREFIX))
async def cb_admin_view_order(
    callback: CallbackQuery,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_ORDER_VIEW_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    order = db.get_order(order_id)
    caption = _order_receipt_caption(db, order)
    if caption is None:
        await callback.answer("سفارش در انتظار بررسی نیست.", show_alert=True)
        return

    user_id = int(order["user_id"])
    review_kb = keyboards.admin_review(order_id=order_id, user_id=user_id)
    file_id = order["screenshot_file_id"]
    admin_chat = callback.from_user.id

    try:
        if file_id:
            sent = await bot.send_photo(
                admin_chat,
                photo=file_id,
                caption=caption,
                reply_markup=review_kb,
            )
            if sent:
                db.add_admin_receipt_message(order_id, admin_chat, sent.message_id)
        else:
            sent = await bot.send_message(
                admin_chat, caption, reply_markup=review_kb
            )
            if sent:
                db.add_admin_receipt_message(order_id, admin_chat, sent.message_id)
    except Exception:  # noqa: BLE001
        await callback.answer("ارسال رسید ناموفق بود.", show_alert=True)
        return
    await callback.answer("رسید ارسال شد ✅")


# ---------- locations detail / toggle / purge prompt ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_DETAIL_PREFIX))
async def cb_admin_loc_detail(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_DETAIL_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return

    sub = escape(loc.sub_url_template) if loc.sub_url_template else "—"
    test_line = ""
    if loc.is_test:
        test_line = (
            f"\n🧪 <b>لوکیشن تست</b> — {texts.format_test_volume()} · "
            f"{texts.TEST_DURATION_DAYS} روز · رایگان · "
            f"دکمه تست: {'روشن' if db.is_test_feature_enabled() else 'خاموش'}\n"
        )
    text = texts.ADMIN_LOC_DETAIL.format(
        id=loc.id,
        state_emoji="🟢" if loc.enabled else "🔴",
        name=escape(loc.name),
        test_line=test_line,
        base_url=escape(loc.base_url),
        inbounds=",".join(str(i) for i in loc.inbound_ids) or "—",
        sub=sub,
        pricing=escape(location_pricing_label(db, loc)),
    )
    if isinstance(callback.message, Message):
        await callback.message.answer(
            text,
            reply_markup=keyboards.admin_location_detail(
                loc.id, enabled=loc.enabled
            ),
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_TOGGLE_PREFIX))
async def cb_admin_loc_toggle(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_TOGGLE_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return

    new_state = not loc.enabled
    db.set_location_enabled(loc_id, new_state)
    state_word = "فعال" if new_state else "غیرفعال"
    await callback.answer(f"لوکیشن {state_word} شد ✅")
    if isinstance(callback.message, Message):
        await send_locations(callback.message, db)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_PURGE_PREFIX))
async def cb_admin_loc_purge_prompt(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_PURGE_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return

    count = db.count_orders_for_location(loc_id)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.PURGE_CONFIRM.format(
                id=loc_id, name=escape(loc.name), count=count
            ),
            reply_markup=keyboards.purge_confirm(loc_id),
        )
    await callback.answer()


# ---------- tools ----------
@router.callback_query(F.data == keyboards.CB_ADM_TOOL_SYNC)
async def cb_admin_tool_sync(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await callback.answer()
    await callback.message.answer(texts.SYNC_PANEL_START)
    for chunk in await run_sync_panel(db):
        await callback.message.answer(chunk)


@router.callback_query(F.data == keyboards.CB_ADM_TOOL_CLEAR)
async def cb_admin_tool_clear(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.answer(run_clear_declined(db))
    await callback.answer("انجام شد ✅")
