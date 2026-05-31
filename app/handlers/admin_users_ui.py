"""Format admin «کاربران» list and user detail (Telegram ↔ panel clients)."""

from __future__ import annotations

from html import escape
import math

from app import texts
from app.db import Database

ADMIN_USERS_PER_PAGE = 8


def _user_display_name(row) -> str:
    last = None
    try:
        last = row["last_name"]
    except (IndexError, KeyError):
        pass
    parts = [row["first_name"], last]
    name = " ".join(p for p in parts if p) or "—"
    return escape(name)


def _format_order_line(order) -> str:
    status = texts.STATUS_BADGE.get(str(order["status"]), escape(str(order["status"])))
    email = order["xui_email"]
    if email:
        panel_line = texts.ADMIN_USER_ORDER_PANEL.format(email=escape(str(email)))
    else:
        panel_line = texts.ADMIN_USER_ORDER_NO_PANEL
    return texts.ADMIN_USER_ORDER_LINE.format(
        order_id=order["id"],
        status=status,
        location=escape(str(order["location_name"])),
        volume=int(order["volume_gb"]),
        days=int(order["duration_days"]),
        price=texts.format_price(int(order["price"])),
        panel_line=panel_line,
    )


def format_users_page(db: Database, page: int = 0) -> tuple[str, int, list]:
    """Return (message_html, total_pages, users_on_page)."""
    total = db.count_users()
    if total == 0:
        return texts.ADMIN_USERS_EMPTY, 1, []

    per_page = ADMIN_USERS_PER_PAGE
    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    users = db.list_users_paginated(page * per_page, per_page)

    lines = [
        texts.ADMIN_USERS_HEADER.format(
            page=page + 1,
            pages=total_pages,
            total=total,
        ),
        "",
    ]

    for u in users:
        username = f"@{u['username']}" if u["username"] else "—"
        ban = "🚫 مسدود" if bool(u["is_banned"]) else "✅ فعال"
        orders = db.list_user_orders_admin(int(u["user_id"]), limit=20)
        with_panel = [o for o in orders if o["xui_email"]]

        lines.append(
            f"▸ <b>{_user_display_name(u)}</b> ({username}) — <code>{u['user_id']}</code> {ban}"
        )
        if with_panel:
            for o in with_panel[:4]:
                st = texts.STATUS_BADGE.get(
                    str(o["status"]), escape(str(o["status"]))
                )
                lines.append(
                    f"   🆔 <code>{escape(str(o['xui_email']))}</code> · "
                    f"{st} · {escape(str(o['location_name']))}"
                )
            if len(with_panel) > 4:
                lines.append(f"   <i>+{len(with_panel) - 4} کلاینت دیگر…</i>")
        elif orders:
            lines.append(f"   <i>{len(orders)} سفارش — هنوز کلاینت پنل ندارد</i>")
        else:
            lines.append("   <i>بدون سفارش</i>")
        lines.append("")

    return "\n".join(lines).rstrip(), total_pages, users


def format_user_detail(db: Database, user_id: int) -> str | None:
    row = db.get_user(user_id)
    if row is None:
        return None

    username = f"@{row['username']}" if row["username"] else "—"
    ban_state = "مسدود 🚫" if bool(row["is_banned"]) else "فعال ✅"
    orders = db.list_user_orders_admin(user_id, limit=30)

    if orders:
        order_lines = [_format_order_line(o) for o in orders]
        orders_block = "\n".join(order_lines)
    else:
        orders_block = texts.ADMIN_USER_NO_ORDERS

    return texts.ADMIN_USER_DETAIL.format(
        user_id=user_id,
        full_name=_user_display_name(row),
        username=username,
        created_at=escape(str(row["created_at"])),
        ban_state=ban_state,
        order_count=len(orders),
        orders_block=orders_block,
    )
