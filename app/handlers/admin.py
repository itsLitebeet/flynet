from __future__ import annotations

import asyncio
import logging
from html import escape

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app import texts
from app.config import Settings
from app.db import Database


router = Router(name="admin")
log = logging.getLogger(__name__)


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def _require_admin(message: Message, settings: Settings) -> bool:
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        # The actual reply is sent by the caller via early return; we only check here.
        return False
    return True


# ---------- generic ----------
@router.message(Command("admin"))
async def cmd_admin(message: Message, settings: Settings) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await message.answer(texts.ADMIN_HELP)


@router.message(Command("stats"))
async def cmd_stats(message: Message, settings: Settings, db: Database) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    await message.answer(
        texts.ADMIN_STATS.format(
            users=db.count_users(),
            orders=db.count_orders(),
            awaiting_payment=db.count_orders_by_status("awaiting_payment"),
            awaiting_review=db.count_orders_by_status("awaiting_review"),
            provisioned=db.count_orders_by_status("provisioned"),
            declined=db.count_orders_by_status("declined"),
            failed=db.count_orders_by_status("failed"),
            tickets=db.count_tickets(),
        )
    )


@router.message(Command("users"))
async def cmd_users(message: Message, settings: Settings, db: Database) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    rows = db.recent_users(limit=20)
    if not rows:
        await message.answer("هیچ کاربری ثبت نشده است.")
        return

    lines = ["👥 <b>۲۰ کاربر اخیر</b>", ""]
    for r in rows:
        username = f"@{r['username']}" if r["username"] else "—"
        first = escape(r["first_name"] or "")
        lines.append(
            f"• <code>{r['user_id']}</code> — {first} ({username}) — {r['created_at']}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    command: CommandObject,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    payload = (command.args or "").strip()
    if not payload:
        await message.answer(texts.BROADCAST_EMPTY)
        return

    user_ids = db.all_user_ids()
    await message.answer(texts.BROADCAST_STARTED.format(count=len(user_ids)))

    ok = 0
    fail = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, payload)
            ok += 1
        except Exception:  # noqa: BLE001 — user may have blocked the bot
            fail += 1
        await asyncio.sleep(0.05)

    await message.answer(texts.BROADCAST_DONE.format(ok=ok, fail=fail))


# ---------- settings ----------
@router.message(Command("setcard"))
async def cmd_setcard(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    if "|" not in raw:
        await message.answer(texts.SET_CARD_USAGE)
        return
    number, _, holder = raw.partition("|")
    number = number.strip()
    holder = holder.strip()
    if not number or not holder:
        await message.answer(texts.SET_CARD_USAGE)
        return

    db.set_setting("card_number", number)
    db.set_setting("card_holder", holder)
    await message.answer(texts.SET_CARD_OK.format(number=escape(number), holder=escape(holder)))


@router.message(Command("setprice"))
async def cmd_setprice(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    parts = (command.args or "").split()
    if len(parts) != 3:
        await message.answer(texts.SET_PRICE_USAGE)
        return
    try:
        base, per_gb, per_day = (int(p) for p in parts)
    except ValueError:
        await message.answer(texts.SET_PRICE_USAGE)
        return
    if min(base, per_gb, per_day) < 0:
        await message.answer(texts.SET_PRICE_USAGE)
        return

    db.set_setting("price_base", str(base))
    db.set_setting("price_per_gb", str(per_gb))
    db.set_setting("price_per_day", str(per_day))
    await message.answer(texts.SET_PRICE_OK.format(base=base, per_gb=per_gb, per_day=per_day))


@router.message(Command("showsettings"))
async def cmd_showsettings(message: Message, settings: Settings, db: Database) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    base, per_gb, per_day = db.get_pricing()
    await message.answer(
        texts.SHOW_SETTINGS.format(
            card_number=escape(db.get_setting("card_number", "—") or "—"),
            card_holder=escape(db.get_setting("card_holder", "—") or "—"),
            base=base,
            per_gb=per_gb,
            per_day=per_day,
        )
    )


# ---------- locations ----------
@router.message(Command("locations"))
async def cmd_locations(message: Message, settings: Settings, db: Database) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    locs = db.list_locations(only_enabled=False)
    if not locs:
        await message.answer(texts.LOC_LIST_EMPTY)
        return

    lines = [texts.LOC_LIST_HEADER]
    for loc in locs:
        lines.append(
            texts.LOC_LIST_ITEM.format(
                id=loc.id,
                state_emoji="🟢" if loc.enabled else "🔴",
                name=escape(loc.name),
                base_url=escape(loc.base_url),
                inbounds=",".join(str(i) for i in loc.inbound_ids) or "—",
            )
        )
    await message.answer("\n\n".join(lines))


def _normalize_panel_url(raw: str) -> str:
    """Strip trailing slashes and a trailing /panel suffix if present.

    Users often paste the full panel URL (https://host/SECRET/panel) but the
    XuiClient appends '/panel/api/...' itself, so we need the root only.
    """
    url = raw.strip().rstrip("/")
    if url.endswith("/panel"):
        url = url[: -len("/panel")]
    return url


@router.message(Command("addlocation"))
async def cmd_addlocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 4 or not all(parts):
        await message.answer(texts.ADD_LOC_USAGE)
        return

    name, base_url, api_token, inbound_str = parts
    base_url = _normalize_panel_url(base_url)
    try:
        inbound_ids = [int(x.strip()) for x in inbound_str.split(",") if x.strip()]
    except ValueError:
        await message.answer(texts.ADD_LOC_USAGE)
        return
    if not inbound_ids:
        await message.answer(texts.ADD_LOC_USAGE)
        return

    loc_id = db.add_location(name=name, base_url=base_url, api_token=api_token,
                              inbound_ids=inbound_ids)
    await message.answer(
        texts.ADD_LOC_OK.format(name=escape(name), id=loc_id)
        + f"\n\n🔗 base_url:\n<code>{escape(base_url)}</code>"
        + f"\n📡 inbounds: <code>{','.join(str(i) for i in inbound_ids)}</code>"
    )


@router.message(Command("dellocation"))
async def cmd_dellocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.DEL_LOC_USAGE)
        return

    result = db.remove_location(loc_id)
    if result == "not_found":
        await message.answer(texts.DEL_LOC_NOTFOUND)
    elif result == "disabled":
        await message.answer(texts.DEL_LOC_DISABLED.format(id=loc_id))
    else:
        await message.answer(texts.DEL_LOC_OK.format(id=loc_id))


@router.message(Command("togglelocation"))
async def cmd_togglelocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.TOGGLE_LOC_USAGE)
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    new_state = not loc.enabled
    db.set_location_enabled(loc_id, new_state)
    await message.answer(
        texts.TOGGLE_LOC_OK.format(id=loc_id, state="فعال" if new_state else "غیرفعال")
    )


# ---------- pending orders ----------
@router.message(Command("pending"))
async def cmd_pending(message: Message, settings: Settings, db: Database) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    rows = db.pending_orders(limit=20)
    if not rows:
        await message.answer(texts.PENDING_EMPTY)
        return

    lines = [texts.PENDING_HEADER]
    for r in rows:
        lines.append(
            texts.PENDING_ITEM.format(
                id=r["id"],
                user_id=r["user_id"],
                volume=r["volume_gb"],
                days=r["duration_days"],
                price=texts.format_price(int(r["price"])),
                created_at=r["created_at"],
            )
        )
    await message.answer("\n".join(lines))
