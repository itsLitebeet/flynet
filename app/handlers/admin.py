from __future__ import annotations

import asyncio
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database, Location
from app.xui import XuiClient, XuiError


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

    number = texts.format_card_number(number)
    db.set_setting("card_number", number)
    db.set_setting("card_holder", holder)
    await message.answer(
        texts.SET_CARD_OK.format(number=escape(number), holder=escape(holder))
    )


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
            card_number=escape(
                texts.format_card_number(db.get_setting("card_number", "—") or "—")
            ),
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
                sub_template=escape(loc.sub_url_template) if loc.sub_url_template else "—",
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
    # 4 required fields, 5th (sub_url_template) is optional
    if len(parts) not in (4, 5) or not all(parts[:4]):
        await message.answer(texts.ADD_LOC_USAGE)
        return

    name, base_url, api_token, inbound_str = parts[:4]
    sub_url_template = parts[4].strip() if len(parts) == 5 and parts[4].strip() else None

    base_url = _normalize_panel_url(base_url)
    try:
        inbound_ids = [int(x.strip()) for x in inbound_str.split(",") if x.strip()]
    except ValueError:
        await message.answer(texts.ADD_LOC_USAGE)
        return
    if not inbound_ids:
        await message.answer(texts.ADD_LOC_USAGE)
        return

    if sub_url_template is not None and "{subId}" not in sub_url_template:
        await message.answer(texts.SET_SUBURL_BAD)
        return

    loc_id = db.add_location(
        name=name,
        base_url=base_url,
        api_token=api_token,
        inbound_ids=inbound_ids,
        sub_url_template=sub_url_template,
    )
    extra_sub_line = (
        f"\n🔔 sub: <code>{escape(sub_url_template)}</code>"
        if sub_url_template else ""
    )
    await message.answer(
        texts.ADD_LOC_OK.format(name=escape(name), id=loc_id)
        + f"\n\n🔗 base_url:\n<code>{escape(base_url)}</code>"
        + f"\n📡 inbounds: <code>{','.join(str(i) for i in inbound_ids)}</code>"
        + extra_sub_line
    )


@router.message(Command("setsuburl"))
async def cmd_setsuburl(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    parts = raw.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(texts.SET_SUBURL_USAGE)
        return
    try:
        loc_id = int(parts[0])
    except ValueError:
        await message.answer(texts.SET_SUBURL_USAGE)
        return

    template_raw = parts[1].strip()
    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    if template_raw == "-":
        db.set_location_sub_url_template(loc_id, None)
        await message.answer(texts.SET_SUBURL_CLEARED.format(id=loc_id))
        return

    if "{subId}" not in template_raw:
        await message.answer(texts.SET_SUBURL_BAD)
        return

    db.set_location_sub_url_template(loc_id, template_raw)
    await message.answer(
        texts.SET_SUBURL_OK.format(id=loc_id, template=escape(template_raw))
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


@router.message(Command("purgelocation"))
async def cmd_purgelocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.PURGE_USAGE)
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    count = db.count_orders_for_location(loc_id)
    await message.answer(
        texts.PURGE_CONFIRM.format(id=loc_id, name=escape(loc.name), count=count),
        reply_markup=keyboards.purge_confirm(loc_id),
    )


@router.callback_query(F.data.startswith(keyboards.CB_PURGE_CONFIRM_PREFIX))
async def cb_purge_confirm(
    callback: CallbackQuery, db: Database, settings: Settings
) -> None:
    if callback.from_user is None or not _is_admin(callback.from_user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_PURGE_CONFIRM_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    # Capture count BEFORE deletion so the success message is accurate.
    count = db.count_orders_for_location(loc_id)
    result = db.purge_location(loc_id)
    if result == "not_found":
        await callback.answer("یافت نشد", show_alert=True)
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.PURGE_DONE.format(id=loc_id, count=count), reply_markup=None
        )
    await callback.answer("حذف شد ✅")


@router.callback_query(F.data == keyboards.CB_PURGE_CANCEL)
async def cb_purge_cancel(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.PURGE_CANCELLED, reply_markup=None)
    await callback.answer()


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


# ---------- panel sync (manual client deletion on 3x-ui) ----------
@router.message(Command("clearorder"))
async def cmd_clearorder(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    """Hard-delete one order from the database."""
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(texts.CLEAR_ORDER_USAGE)
        return

    if not db.delete_order(order_id):
        await message.answer(texts.CLEAR_ORDER_NOTFOUND)
        return
    await message.answer(texts.CLEAR_ORDER_OK.format(id=order_id))


@router.message(Command("cleardeclined"))
async def cmd_cleardeclined(message: Message, settings: Settings, db: Database) -> None:
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    count = db.delete_orders_by_status("declined")
    if count == 0:
        await message.answer(texts.CLEAR_DECLINED_NONE)
    else:
        await message.answer(texts.CLEAR_DECLINED_OK.format(count=count))


async def _sync_location_orders(db: Database, loc: Location) -> tuple[list[int], str | None]:
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


@router.message(Command("syncpanel"))
async def cmd_syncpanel(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    """Compare bot DB with panel /clients/list and clear orphaned orders."""
    if not _require_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    raw = (command.args or "").strip()
    loc_filter: int | None = None
    if raw:
        try:
            loc_filter = int(raw)
        except ValueError:
            await message.answer(texts.SYNC_PANEL_USAGE)
            return
        if db.get_location(loc_filter) is None:
            await message.answer(texts.DEL_LOC_NOTFOUND)
            return

    await message.answer(texts.SYNC_PANEL_START)

    locations = db.list_locations(only_enabled=False)
    if loc_filter is not None:
        loc = db.get_location(loc_filter)
        locations = [loc] if loc else []

    all_cleared: list[int] = []
    for loc in locations:
        cleared, err = await _sync_location_orders(db, loc)
        if err:
            await message.answer(
                texts.SYNC_PANEL_LOC_ERR.format(
                    id=loc.id, name=escape(loc.name), error=escape(err)
                )
            )
            continue
        all_cleared.extend(cleared)

    declined_deleted = db.delete_orders_by_status("declined")

    if not all_cleared and declined_deleted == 0:
        await message.answer(texts.SYNC_PANEL_NONE.format(declined=0))
        return

    orphan_ids = ", ".join(str(i) for i in all_cleared) if all_cleared else "—"
    await message.answer(
        texts.SYNC_PANEL_DONE.format(
            orphan_count=len(all_cleared),
            orphan_ids=orphan_ids,
            declined=declined_deleted,
        )
    )
