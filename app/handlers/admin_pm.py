from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ContentType, ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import TOOLS_BROADCAST
from app.handlers.admin_helpers import (
    admin_can,
    guard_admin_callback,
    guard_admin_message,
)
from app.logs import Actor, make_logger

router = Router(name="admin_pm")
log = logging.getLogger(__name__)

class PrivateMessageFlow(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()

# Callback constants
CB_PM_CONFIRM = "pm:send"
CB_PM_CANCEL = "pm:cancel"

_CONTENT_TYPE_FA: dict[str, str] = {
    ContentType.TEXT.value: "متن",
    ContentType.PHOTO.value: "عکس",
    ContentType.VIDEO.value: "ویدیو",
    ContentType.DOCUMENT.value: "فایل",
    ContentType.ANIMATION.value: "گیف",
    ContentType.AUDIO.value: "صوت",
    ContentType.VOICE.value: "ویس",
    ContentType.VIDEO_NOTE.value: "ویدیو دایره‌ای",
    ContentType.STICKER.value: "استیکر",
}

def _content_type_label(content_type: str) -> str:
    return _CONTENT_TYPE_FA.get(content_type, content_type)

def _caption_preview(message: Message, *, max_len: int = 120) -> str:
    cap = (message.caption or message.text or "").strip()
    if not cap:
        return "—"
    if len(cap) > max_len:
        return cap[: max_len - 1] + "…"
    return cap

def pm_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ ارسال پیام", callback_data=CB_PM_CONFIRM),
                InlineKeyboardButton(text="❌ انصراف", callback_data=CB_PM_CANCEL),
            ]
        ]
    )

def pm_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ انصراف", callback_data=CB_PM_CANCEL),
            ]
        ]
    )

async def find_user_by_query(db: Database, query: str) -> dict | None:
    """Finds user_id, username, first_name, last_name by order ID, user ID, username, or name."""
    query = query.strip()
    if not query:
        return None

    # Case 1: Numeric lookup (User ID or Order ID)
    if query.isdigit():
        val = int(query)
        # Check if it's a User ID
        async with db._cursor() as cur:
            await cur.execute(
                "SELECT user_id, username, first_name, last_name FROM users WHERE user_id = ?",
                (val,),
            )
            row = await cur.fetchone()
            if row:
                return dict(row)

            # Check if it's an Order ID
            await cur.execute("SELECT user_id FROM orders WHERE id = ?", (val,))
            row_order = await cur.fetchone()
            if row_order:
                uid = row_order["user_id"]
                await cur.execute(
                    "SELECT user_id, username, first_name, last_name FROM users WHERE user_id = ?",
                    (uid,),
                )
                row_user = await cur.fetchone()
                if row_user:
                    return dict(row_user)

    # Case 2: Username / name lookup (LOWER username search without @)
    username = query.lstrip("@")
    async with db._cursor() as cur:
        await cur.execute(
            "SELECT user_id, username, first_name, last_name FROM users WHERE LOWER(username) = LOWER(?)",
            (username,),
        )
        row = await cur.fetchone()
        if row:
            return dict(row)

        # Try finding by first name or last name
        await cur.execute(
            "SELECT user_id, username, first_name, last_name FROM users WHERE LOWER(first_name) = LOWER(?) OR LOWER(last_name) = LOWER(?)",
            (username, username),
        )
        row = await cur.fetchone()
        if row:
            return dict(row)

    return None

# ---------- entry point via command ----------
@router.message(Command("pm", "msg"), StateFilter(None))
async def cmd_pm_entry(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_BROADCAST):
        return

    text = message.text or ""
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        usage = (
            "💬 <b>نحوه استفاده از دستور ارسال پیام خصوصی:</b>\n"
            "<code>/pm &lt;یوزرنیم یا شماره سفارش&gt; &lt;متن پیام&gt;</code>\n"
            "یا فقط <code>/pm &lt;یوزرنیم یا شماره سفارش&gt;</code> برای ارسال پیام چندرسانه‌ای.\n\n"
            "مثال‌ها:\n"
            "<code>/pm @awwsuchسلام خوبی؟</code>\n"
            "<code>/pm 115پیام به صاحب سفارش شماره 115</code>"
        )
        await message.answer(usage, parse_mode=ParseMode.HTML)
        return

    target_query = parts[1].strip()
    user_record = await find_user_by_query(db, target_query)
    if not user_record:
        await message.answer(
            "❌ کاربر یافت نشد.\n"
            "می‌توانید از یوزرنیم تلگرام (با یا بدون @)، آیدی عددی تلگرام، یا آیدی سفارش (مثلا 115) استفاده کنید.",
            parse_mode=ParseMode.HTML,
        )
        return

    target_uid = int(user_record["user_id"])
    first_name = user_record["first_name"] or ""
    last_name = user_record["last_name"] or ""
    full_name = " ".join(p for p in [first_name, last_name] if p) or "—"
    username = user_record["username"] or "—"

    # If message text was provided inline
    if len(parts) == 3:
        msg_text = parts[2].strip()
        await state.update_data(
            target_id=target_uid,
            full_name=full_name,
            username=username,
            content_type="text",
            message_text=msg_text,
            is_quick_cmd=True,
        )
        await state.set_state(PrivateMessageFlow.waiting_confirm)

        username_str = f" · @{username}" if username != "—" else ""
        preview = (
            f"🔍 <b>پیش‌نمایش پیام خصوصی به:</b>\n"
            f"👤 <b>{escape(full_name)}</b> (<code>{target_uid}</code>){username_str}\n\n"
            f"نوع پیام: <b>متن</b>\n"
            f"محتوا:\n"
            f"<blockquote>{escape(msg_text)}</blockquote>\n\n"
            f"آیا از ارسال این پیام اطمینان دارید؟"
        )
        await message.answer(preview, reply_markup=pm_confirm_keyboard(), parse_mode=ParseMode.HTML)
    else:
        # Start interactive FSM flow
        await state.update_data(
            target_id=target_uid,
            full_name=full_name,
            username=username,
            is_quick_cmd=False,
        )
        await state.set_state(PrivateMessageFlow.waiting_content)

        username_str = f" · @{username}" if username != "—" else ""
        prompt = (
            f"📩 <b>ارسال پیام خصوصی به:</b>\n"
            f"👤 <b>{escape(full_name)}</b> (<code>{target_uid}</code>){username_str}\n\n"
            f"لطفاً پیام خود را ارسال کنید (پیام می‌تواند شامل متن، عکس، ویدیو، ویس یا فایل باشد):"
        )
        await message.answer(prompt, reply_markup=pm_cancel_keyboard(), parse_mode=ParseMode.HTML)

# ---------- entry point via callback button (from customer detail card) ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_PM_PREFIX), StateFilter(None))
async def cb_pm_entry(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_callback(callback, settings, db, TOOLS_BROADCAST):
        return

    raw_uid = callback.data.removeprefix(keyboards.CB_ADM_PM_PREFIX)
    try:
        target_uid = int(raw_uid)
    except ValueError:
        await callback.answer()
        return

    user_record = await find_user_by_query(db, str(target_uid))
    if not user_record:
        await callback.answer("کاربر یافت نشد ❌", show_alert=True)
        return

    first_name = user_record["first_name"] or ""
    last_name = user_record["last_name"] or ""
    full_name = " ".join(p for p in [first_name, last_name] if p) or "—"
    username = user_record["username"] or "—"

    await state.update_data(
        target_id=target_uid,
        full_name=full_name,
        username=username,
        is_quick_cmd=False,
    )
    await state.set_state(PrivateMessageFlow.waiting_content)

    username_str = f" · @{username}" if username != "—" else ""
    prompt = (
        f"📩 <b>ارسال پیام خصوصی به:</b>\n"
        f"👤 <b>{escape(full_name)}</b> (<code>{target_uid}</code>){username_str}\n\n"
        f"لطفاً پیام خود را ارسال کنید (پیام می‌تواند شامل متن، عکس، ویدیو، ویس یا فایل باشد):"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            prompt,
            reply_markup=pm_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()

# ---------- cancel ----------
@router.callback_query(F.data == CB_PM_CANCEL, StateFilter(PrivateMessageFlow))
async def cb_pm_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    user_id = callback.from_user.id
    if not await admin_can(user_id, TOOLS_BROADCAST, settings, db):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return

    await state.clear()
    text = "❌ ارسال پیام لغو شد."
    kb = await keyboards.admin_reply_keyboard(user_id, settings, db)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=None)
        # Send a fresh home reply keyboard to admin
        await callback.message.answer("بازگشت به منوی ادمین 🏠", reply_markup=kb)
    await callback.answer()

# ---------- receive content ----------
@router.message(StateFilter(PrivateMessageFlow.waiting_content))
async def on_pm_content(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_BROADCAST):
        return

    if message.media_group_id:
        await message.answer("⚠️ ارسال پیام‌های آلبومی (مدیاگروپ) پشتیبانی نمی‌شود. لطفاً پیام را به صورت تکی بفرستید.")
        return

    if message.from_user is None or message.chat is None:
        return

    data = await state.get_data()
    target_id = int(data["target_id"])
    full_name = data["full_name"]
    username = data["username"]

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        content_type=message.content_type,
    )
    await state.set_state(PrivateMessageFlow.waiting_confirm)

    username_str = f" · @{username}" if username != "—" else ""
    preview = (
        f"🔍 <b>پیش‌نمایش پیام خصوصی به:</b>\n"
        f"👤 <b>{escape(full_name)}</b> (<code>{target_id}</code>){username_str}\n\n"
        f"نوع پیام: <b>{_content_type_label(message.content_type)}</b>\n"
        f"محتوا: {escape(_caption_preview(message))}\n\n"
        f"آیا از ارسال این پیام اطمینان دارید؟"
    )
    await message.answer(
        preview,
        reply_markup=pm_confirm_keyboard(),
        parse_mode=ParseMode.HTML,
    )

# ---------- confirm & send ----------
@router.callback_query(F.data == CB_PM_CONFIRM, StateFilter(PrivateMessageFlow.waiting_confirm))
async def cb_pm_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_callback(callback, settings, db, TOOLS_BROADCAST):
        return

    data = await state.get_data()
    target_id = int(data["target_id"])
    full_name = data["full_name"]
    username = data["username"]
    is_quick_cmd = data.get("is_quick_cmd", False)

    await state.clear()

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await callback.message.edit_text("⏳ در حال ارسال...", reply_markup=None)

    success = False
    try:
        # 1. Send header notify first to client
        await bot.send_message(
            chat_id=target_id,
            text="📩 <b>پیام جدید از طرف مدیریت:</b>",
            parse_mode=ParseMode.HTML,
        )

        # 2. Deliver message
        if is_quick_cmd:
            msg_text = data["message_text"]
            await bot.send_message(chat_id=target_id, text=msg_text)
        else:
            from_chat_id = int(data["from_chat_id"])
            message_id = int(data["message_id"])
            await bot.copy_message(
                chat_id=target_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
        success = True
    except Exception as e:
        log.warning("Failed to send private message to %s: %s", target_id, e)

    uid = callback.from_user.id
    admin_kb = await keyboards.admin_reply_keyboard(uid, settings, db)

    if success:
        await callback.message.answer(
            "✅ پیام خصوصی با موفقیت به کاربر ارسال شد.",
            reply_markup=admin_kb,
        )
        # Log to bot logging channel
        admin_actor = Actor.from_user(callback.from_user)
        if admin_actor is not None:
            await make_logger(bot, db).log_admin_action(
                f"👮 ادمین {admin_actor.mention} یک پیام خصوصی به کاربر "
                f"<b>{escape(full_name)}</b> (<code>{target_id}</code>) ارسال کرد."
            )
    else:
        await callback.message.answer(
            "❌ ارسال پیام ناموفق بود.\n"
            "کاربر احتمالاً ربات را مسدود کرده است یا وجود ندارد.",
            reply_markup=admin_kb,
        )

    await callback.answer()
