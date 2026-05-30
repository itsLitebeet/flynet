"""Shared helpers for admin commands and admin panel UI."""

from __future__ import annotations

from html import escape

from aiogram.types import Message

from app import texts
from app.config import Settings
from app.db import Database, Location
from app.xui import XuiClient, XuiError


def is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def admin_from_message(message: Message, settings: Settings) -> bool:
    return message.from_user is not None and is_admin(message.from_user.id, settings)


def normalize_panel_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if url.endswith("/panel"):
        url = url[: -len("/panel")]
    return url


def location_pricing_label(db: Database, loc) -> str:
    base, per_gb, per_day = db.get_pricing_for_location(loc.id)
    uses_global = (
        loc.price_base is None
        and loc.price_per_gb is None
        and loc.price_per_day is None
    )
    tag = "پیش‌فرض" if uses_global else "اختصاصی"
    return f"{tag} — {texts.format_pricing_formula(base, per_gb, per_day)}"


def format_stats_text(db: Database) -> str:
    return texts.ADMIN_STATS.format(
        users=db.count_users(),
        orders=db.count_orders(),
        awaiting_payment=db.count_orders_by_status("awaiting_payment"),
        awaiting_review=db.count_orders_by_status("awaiting_review"),
        provisioned=db.count_orders_by_status("provisioned"),
        declined=db.count_orders_by_status("declined"),
        failed=db.count_orders_by_status("failed"),
        tickets=db.count_tickets(),
    )


def format_settings_text(db: Database) -> str:
    base, per_gb, per_day = db.get_pricing()
    return texts.ADMIN_SETTINGS_VIEW.format(
        card_number=escape(
            texts.format_card_number(db.get_setting("card_number", "—") or "—")
        ),
        card_holder=escape(db.get_setting("card_holder", "—") or "—"),
        base=base,
        per_gb=per_gb,
        per_day=per_day,
    )


async def sync_location_orders(
    db: Database, loc: Location
) -> tuple[list[int], str | None]:
    """Return (cleared_order_ids, error_message)."""
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            clients = await xui.list_clients()
    except XuiError as exc:
        return [], str(exc)

    panel_emails = {str(c.get("email", "")) for c in clients if c.get("email")}
    cleared: list[int] = []
    for row in db.list_provisioned_orders(location_id=loc.id):
        email = row["xui_email"]
        if not email:
            continue
        if str(email) not in panel_emails:
            oid = int(row["id"])
            if db.delete_order(oid):
                cleared.append(oid)
    return cleared, None


async def run_sync_panel(
    db: Database, loc_filter: int | None = None
) -> list[str]:
    """Messages to send after a panel sync (excluding the initial 'started' line)."""
    locations = db.list_locations(only_enabled=False)
    if loc_filter is not None:
        loc = db.get_location(loc_filter)
        locations = [loc] if loc else []

    all_cleared: list[int] = []
    out: list[str] = []
    for loc in locations:
        if loc is None:
            continue
        cleared, err = await sync_location_orders(db, loc)
        if err:
            out.append(
                texts.SYNC_PANEL_LOC_ERR.format(
                    id=loc.id, name=escape(loc.name), error=escape(err)
                )
            )
            continue
        all_cleared.extend(cleared)

    declined_deleted = db.delete_orders_by_status("declined")
    if not all_cleared and declined_deleted == 0:
        out.append(texts.SYNC_PANEL_NONE.format(declined=0))
    else:
        orphan_ids = ", ".join(str(i) for i in all_cleared) if all_cleared else "—"
        out.append(
            texts.SYNC_PANEL_DONE.format(
                orphan_count=len(all_cleared),
                orphan_ids=orphan_ids,
                declined=declined_deleted,
            )
        )
    return out


def run_clear_declined(db: Database) -> str:
    declined = db.delete_orders_by_status("declined")
    unpaid = db.delete_orders_by_status("awaiting_payment")
    total = declined + unpaid
    if total == 0:
        return texts.CLEAR_DECLINED_NONE
    return texts.CLEAR_DECLINED_OK.format(
        declined=declined, unpaid=unpaid, total=total
    )
