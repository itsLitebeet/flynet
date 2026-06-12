"""Format admin order detail text."""

from __future__ import annotations

from html import escape

from app import texts
from app.db import Database


async def _user_label(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    if row is None:
        return f"<code>{user_id}</code>"
    try:
        last = row["last_name"]
    except (KeyError, IndexError):
        last = None
    name = " ".join(p for p in [row["first_name"], last] if p) or "—"
    uname = f"@{row['username']}" if row["username"] else "—"
    return (
        f"<a href='tg://user?id={user_id}'>{escape(name)}</a> "
        f"(<code>{user_id}</code>) · {escape(uname)}"
    )


async def _admin_reviewer_label(db: Database, admin_id: int | None) -> str:
    if admin_id is None:
        return "—"
    return await _user_label(db, int(admin_id))


async def format_admin_order_detail(db: Database, order_id: int) -> str | None:
    order = await db.get_order(order_id)
    if order is None:
        return None

    status = texts.STATUS_BADGE.get(str(order["status"]), escape(str(order["status"])))
    is_test = bool(order["is_test"]) if "is_test" in order.keys() else False
    vol = (
        texts.format_test_volume()
        if is_test
        else f"{int(order['volume_gb'])} گیگابایت"
    )
    nick = escape(str(order["nickname"])) if order["nickname"] else "—"
    panel_email = escape(str(order["xui_email"])) if order["xui_email"] else "—"
    sub_id = escape(str(order["xui_sub_id"])) if order["xui_sub_id"] else "—"
    decline = escape(str(order["decline_reason"])) if order["decline_reason"] else "—"
    screenshot = "✅" if order["screenshot_file_id"] else "—"

    return texts.ADMIN_ORDER_DETAIL.format(
        order_id=order_id,
        status=status,
        user_line=await _user_label(db, int(order["user_id"])),
        location=escape(str(order["location_name"])),
        location_id=int(order["location_id"]),
        volume=vol,
        days=int(order["duration_days"]),
        price=texts.format_price(int(order["price"])),
        nickname=nick,
        panel_email=panel_email,
        sub_id=sub_id,
        reviewer=await _admin_reviewer_label(
            db, int(order["admin_id"]) if order["admin_id"] is not None else None
        ),
        decline_reason=decline,
        screenshot=screenshot,
        created_at=escape(str(order["created_at"])),
        updated_at=escape(str(order["updated_at"])),
        test_mark="🧪 بله" if is_test else "خیر",
    )
