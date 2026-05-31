"""Shared admin UI helpers (edit-in-place, formatted menus)."""

from __future__ import annotations

from html import escape

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from app import texts
from app.db import Database


async def admin_edit_or_answer(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    edit_in_place: bool = False,
) -> None:
    """Prefer editing the current message; fall back to a new one."""
    if edit_in_place:
        try:
            await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return
        except TelegramBadRequest as exc:
            if "message is not modified" not in (exc.message or "").lower():
                pass
    await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )


def format_services_list_text(db: Database, *, loc_filter: int | None = None) -> str:
    packages = (
        db.list_service_packages(loc_filter, only_enabled=False)
        if loc_filter is not None
        else db.list_all_service_packages()
    )
    mode = "روشن ✅" if db.is_manual_purchase_enabled() else "خاموش ❌"
    if not packages:
        body = texts.LIST_SERVICES_EMPTY
    else:
        filter_line = f" — لوکیشن <code>#{loc_filter}</code>" if loc_filter else ""
        lines = [texts.LIST_SERVICES_HEADER.format(filter_line=filter_line)]
        from app.pricing import format_price_with_offer

        offer = db.get_offer_config()
        for pkg in packages:
            loc = db.get_location(pkg.location_id)
            loc_name = escape(loc.name) if loc else "—"
            base = int(pkg.price)
            final = db.resolve_price(base)
            if offer.is_active and final < base:
                price_label = format_price_with_offer(base, final)
            else:
                price_label = texts.format_price(base)
            lines.append(
                texts.LIST_SERVICES_LINE.format(
                    id=pkg.id,
                    loc_id=pkg.location_id,
                    loc_name=loc_name,
                    volume=pkg.volume_gb,
                    days=pkg.duration_days,
                    price=price_label,
                )
            )
        body = "\n".join(lines)
    return texts.ADMIN_SERVICES_MENU.format(
        manual_mode=mode,
        packages_block=body,
    )


def format_tools_menu_text(db: Database) -> str:
    log_id = db.get_log_channel_id()
    log_line = (
        f"متصل: <code>{log_id}</code> ✅"
        if log_id
        else "غیرفعال ❌"
    )
    test_line = "روشن ✅" if db.is_test_feature_enabled() else "خاموش ❌"
    return texts.ADMIN_TOOLS_MENU.format(
        log_channel=log_line,
        test_sub=test_line,
    )
