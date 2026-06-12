from __future__ import annotations

import asyncio
import logging
import time
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.db import Database
from app.xui import XuiClient, XuiError

log = logging.getLogger(__name__)

async def check_and_notify_users(bot: Bot, db: Database) -> None:
    log.info("Starting periodic service checks...")
    orders = await db.list_provisioned_orders()
    log.info("Found %d provisioned services to check.", len(orders))
    
    location_cache = {}
    
    for order in orders:
        user_id = order["user_id"]
        order_id = order["id"]
        email = order["xui_email"]
        loc_id = order["location_id"]
        
        if not email:
            continue
            
        # Check if we already sent both warnings so we don't call X-UI for this client
        traffic_sent = bool(order["traffic_warning_sent"])
        expiry_sent = bool(order["expiry_warning_sent"])
        if traffic_sent and expiry_sent:
            continue
            
        if loc_id not in location_cache:
            location_cache[loc_id] = await db.get_location(loc_id)
            
        location = location_cache[loc_id]
        if not location:
            continue
            
        try:
            async with XuiClient(location.base_url, location.api_token) as xui:
                usage = await xui.get_usage(str(email))
        except XuiError as e:
            log.warning("Could not get usage for client %s in scheduler: %s", email, e)
            continue
        except Exception as e:
            log.warning("Unexpected error checking client %s in scheduler: %s", email, e)
            continue

        nickname = order["nickname"] or email
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="♻️ تمدید سرویس", callback_data=f"my:rn:{order_id}")
        ]])

        # 1. Traffic Check
        if not usage.is_unlimited_traffic and not traffic_sent:
            remaining_gb = usage.remaining_bytes / (1024**3)
            total_gb = usage.total_bytes / (1024**3)
            percent = (usage.remaining_bytes / usage.total_bytes) * 100
            
            if percent < 10.0 or remaining_gb < 1.0:
                text = (
                    f"⚠️ <b>هشدار ترافیک رو به اتمام</b>\n\n"
                    f"کاربر گرامی، ترافیک سرویس شما به پایان خود نزدیک است:\n"
                    f"👤 نام سرویس: <code>{nickname}</code>\n"
                    f"💾 ترافیک باقی‌مانده: {remaining_gb:.2f} گیگابایت از {total_gb:.2f} گیگابایت ({percent:.1f}%)\n\n"
                    f"جهت جلوگیری از قطعی، می‌توانید با زدن دکمه زیر اقدام به تمدید کنید."
                )
                try:
                    await bot.send_message(user_id, text, reply_markup=keyboard)
                    await db.set_order_warning_sent(order_id, traffic_warning=True)
                    log.info("Sent traffic warning to user %d for order %d", user_id, order_id)
                except Exception as e:
                    log.warning("Failed to send traffic warning message to user %d: %s", user_id, e)

        # 2. Expiry Check
        if not usage.is_never_expires and not expiry_sent:
            remaining_time_ms = usage.expiry_time_ms - int(time.time() * 1000)
            remaining_hours = remaining_time_ms / (1000 * 3600)
            
            if 0 < remaining_hours < 24:
                text = (
                    f"⚠️ <b>هشدار انقضای سرویس</b>\n\n"
                    f"کاربر گرامی، زمان سرویس شما به پایان خود نزدیک است:\n"
                    f"👤 نام سرویس: <code>{nickname}</code>\n"
                    f"⏰ زمان باقی‌مانده: {remaining_hours:.1f} ساعت\n\n"
                    f"جهت جلوگیری از قطعی، می‌توانید با زدن دکمه زیر اقدام به تمدید کنید."
                )
                try:
                    await bot.send_message(user_id, text, reply_markup=keyboard)
                    await db.set_order_warning_sent(order_id, expiry_warning=True)
                    log.info("Sent expiry warning to user %d for order %d", user_id, order_id)
                except Exception as e:
                    log.warning("Failed to send expiry warning message to user %d: %s", user_id, e)

async def run_scheduler(bot: Bot, db: Database) -> None:
    log.info("Scheduler task started.")
    # Wait 30 seconds after startup before running the first check to allow the bot to warm up
    await asyncio.sleep(30)
    while True:
        try:
            await check_and_notify_users(bot, db)
        except Exception as e:
            log.exception("Error in scheduler loop execution: %s", e)
        # Sleep for 6 hours
        await asyncio.sleep(3600 * 6)
