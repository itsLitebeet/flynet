from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app import texts
from app.db import Location


# ---------- callback data namespaces ----------
# Top menu
CB_MAIN_BUY           = "main:buy"
CB_MAIN_MY_SERVICES   = "main:my"
CB_MAIN_ACCOUNT       = "main:account"
CB_MAIN_SUPPORT       = "main:support"
CB_MAIN_HELP          = "main:help"
CB_MAIN_ABOUT         = "main:about"
CB_MAIN_TEST          = "main:test"
CB_MAIN_HOME          = "main:home"

# Order flow
CB_LOC_PREFIX     = "loc:"          # loc:<location_id>
CB_VOL_PREFIX     = "vol:"          # vol:<gb> or vol:custom
CB_VOL_CUSTOM     = "vol:custom"
CB_DUR_PREFIX     = "dur:"          # dur:<days>
CB_SVC_PREFIX     = "svc:"          # svc:<package_id>
CB_ORDER_BACK_PKG = "ord:back:pkg"
CB_ORDER_CONFIRM  = "ord:confirm"   # final confirmation of summary
CB_ORDER_CANCEL   = "ord:cancel"
CB_ORDER_BACK_LOC = "ord:back:loc"
CB_ORDER_BACK_VOL = "ord:back:vol"
CB_ORDER_BACK_DUR = "ord:back:dur"

# Support
CB_CANCEL_SUPPORT = "support:cancel"

# Admin review
CB_ADMIN_ACCEPT_PREFIX  = "adm:acc:"   # adm:acc:<order_id>
CB_ADMIN_DECLINE_PREFIX = "adm:dec:"   # adm:dec:<order_id>

# Admin panel navigation
CB_ADM_HOME              = "adm:home"
CB_ADM_DASH              = "adm:dash"
CB_ADM_PENDING_LIST      = "adm:plist"
CB_ADM_SETTINGS          = "adm:set"
CB_ADM_LOCATIONS_LIST    = "adm:llist"
CB_ADM_TOOLS             = "adm:tools"
CB_ADM_USERS                 = "adm:usr"
CB_ADM_USERS_PAGE_PREFIX     = "adm:usrp:"   # adm:usrp:<page>
CB_ADM_USER_DETAIL_PREFIX    = "adm:u:"      # adm:u:<user_id>
CB_ADM_CMD_HELP          = "adm:cmdhelp"
CB_ADM_ORDER_VIEW_PREFIX = "adm:ov:"    # adm:ov:<order_id>
CB_ADM_LOC_DETAIL_PREFIX = "adm:ld:"    # adm:ld:<location_id>
CB_ADM_LOC_TOGGLE_PREFIX = "adm:lt:"    # adm:lt:<location_id>
CB_ADM_TOOL_SYNC         = "adm:tsync"
CB_ADM_TOOL_CLEAR        = "adm:tclr"
CB_ADM_BROADCAST         = "adm:bcast"
CB_BROADCAST_CONFIRM     = "adm:bcast:ok"
CB_BROADCAST_CANCEL      = "adm:bcast:no"
CB_ADM_PLANS             = "adm:plans"
CB_ADM_VOL_DEL_PREFIX    = "adm:vd:"   # adm:vd:<gb>
CB_ADM_DUR_DEL_PREFIX    = "adm:dd:"   # adm:dd:<days>
CB_ADM_LOC_PURGE_PREFIX  = "adm:pg:"   # adm:pg:<location_id> → purge confirm

# Admin destructive actions (require explicit confirmation)
CB_PURGE_CONFIRM_PREFIX = "adm:prg:ok:"  # adm:prg:ok:<location_id>
CB_PURGE_CANCEL         = "adm:prg:no"

# My services
CB_MY_LIST                  = "my:list"
CB_MY_DETAIL_PREFIX         = "my:o:"        # my:o:<order_id>
CB_MY_CONFIGS_PREFIX        = "my:cfg:"      # my:cfg:<order_id>
CB_MY_REFRESH_USAGE_PREFIX  = "my:ref:"      # my:ref:<order_id> — refresh usage on detail
CB_MY_TOGGLE_PREFIX         = "my:tog:"      # my:tog:<order_id>
CB_MY_RENAME_PREFIX         = "my:ren:"      # my:ren:<order_id>
CB_MY_REGEN_PREFIX          = "my:rg:"       # my:rg:<order_id>      (asks confirmation)
CB_MY_REGEN_CONFIRM_PREFIX  = "my:rg!ok:"    # my:rg!ok:<order_id>   (actually regen)


# ---------- reply keyboard (bottom menu, replaces phone keyboard) ----------
def main_reply_keyboard(*, show_test: bool = False) -> ReplyKeyboardMarkup:
    """Persistent bottom buttons — main navigation for buyers."""
    rows: list[list[KeyboardButton]] = []
    if show_test:
        rows.append([KeyboardButton(text=texts.BTN_TEST_SUB)])
    rows.extend([
        [
            KeyboardButton(text=texts.BTN_BUY),
            KeyboardButton(text=texts.BTN_MY_SERVICES),
        ],
        [
            KeyboardButton(text=texts.BTN_MY_ACCOUNT),
            KeyboardButton(text=texts.BTN_SUPPORT),
        ],
        [
            KeyboardButton(text=texts.BTN_HELP),
            KeyboardButton(text=texts.BTN_ABOUT),
        ],
    ])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )


def hide_reply_keyboard() -> ReplyKeyboardRemove:
    """Hide bottom buttons during wizards (order, support, rename)."""
    return ReplyKeyboardRemove()


# All main-menu button labels — use with F.text.in_(...) + StateFilter(None).
MAIN_MENU_BUTTONS = frozenset({
    texts.BTN_BUY,
    texts.BTN_TEST_SUB,
    texts.BTN_MY_SERVICES,
    texts.BTN_MY_ACCOUNT,
    texts.BTN_SUPPORT,
    texts.BTN_HELP,
    texts.BTN_ABOUT,
})

ADMIN_MENU_BUTTONS = frozenset({
    texts.ADMIN_BTN_DASHBOARD,
    texts.ADMIN_BTN_PENDING,
    texts.ADMIN_BTN_SETTINGS,
    texts.ADMIN_BTN_LOCATIONS,
    texts.ADMIN_BTN_TOOLS,
    texts.ADMIN_BTN_USERS,
    texts.ADMIN_BTN_PANEL,
})


# ---------- inline keyboards (inside messages / wizards) ----------
def main_menu(*, show_test: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if show_test:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_TEST_SUB, callback_data=CB_MAIN_TEST
            ),
        ])
    rows.extend([
        [
            InlineKeyboardButton(text=texts.BTN_BUY,         callback_data=CB_MAIN_BUY),
            InlineKeyboardButton(text=texts.BTN_MY_SERVICES, callback_data=CB_MAIN_MY_SERVICES),
        ],
        [
            InlineKeyboardButton(text=texts.BTN_MY_ACCOUNT, callback_data=CB_MAIN_ACCOUNT),
            InlineKeyboardButton(text=texts.BTN_SUPPORT,    callback_data=CB_MAIN_SUPPORT),
        ],
        [
            InlineKeyboardButton(text=texts.BTN_HELP,  callback_data=CB_MAIN_HELP),
            InlineKeyboardButton(text=texts.BTN_ABOUT, callback_data=CB_MAIN_ABOUT),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def test_sub_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_CONFIRM, callback_data="test:confirm"
                ),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_MAIN_HOME),
            ],
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME)]
        ]
    )


# ---------- order flow ----------
def locations(locations: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locations:
        rows.append(
            [InlineKeyboardButton(text=loc.name, callback_data=f"{CB_LOC_PREFIX}{loc.id}")]
        )
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _chunk_buttons(
    buttons: list[InlineKeyboardButton], per_row: int = 3
) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for btn in buttons:
        row.append(btn)
        if len(row) >= per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def volumes(volume_presets_gb: list[int]) -> InlineKeyboardMarkup:
    preset_btns = [
        InlineKeyboardButton(text=f"{gb} GB", callback_data=f"{CB_VOL_PREFIX}{gb}")
        for gb in volume_presets_gb
    ]
    rows = _chunk_buttons(preset_btns, per_row=3)
    rows.append([InlineKeyboardButton(text=texts.BTN_CUSTOM, callback_data=CB_VOL_CUSTOM)])
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_LOC)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def durations(duration_presets_days: list[int]) -> InlineKeyboardMarkup:
    preset_btns = [
        InlineKeyboardButton(text=f"{d} روزه", callback_data=f"{CB_DUR_PREFIX}{d}")
        for d in duration_presets_days
    ]
    rows = _chunk_buttons(preset_btns, per_row=3)
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_VOL)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def service_packages(packages: list) -> InlineKeyboardMarkup:
    """Predefined plans: two buttons per row (volume | days | price)."""
    preset_btns = [
        InlineKeyboardButton(
            text=texts.format_service_package_button(
                pkg.volume_gb, pkg.duration_days, pkg.price
            ),
            callback_data=f"{CB_SVC_PREFIX}{pkg.id}",
        )
        for pkg in packages
    ]
    rows = _chunk_buttons(preset_btns, per_row=2)
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_LOC)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order(*, back_callback: str = CB_ORDER_BACK_DUR) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data=CB_ORDER_CONFIRM)],
            [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=back_callback)],
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ORDER_CANCEL)],
        ]
    )


def cancel_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ORDER_CANCEL)]
        ]
    )


# ---------- support ----------
def cancel_support() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_CANCEL_SUPPORT)]
        ]
    )


# ---------- admin destructive confirmation ----------
def purge_confirm(location_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ بله، پاک کن",
                    callback_data=f"{CB_PURGE_CONFIRM_PREFIX}{location_id}",
                ),
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data=CB_PURGE_CANCEL
                ),
            ]
        ]
    )


# ---------- my services ----------
def my_services_list(orders: list[dict]) -> InlineKeyboardMarkup:
    """`orders` is a list of dicts with keys: id, label."""
    rows: list[list[InlineKeyboardButton]] = []
    for o in orders:
        rows.append([
            InlineKeyboardButton(text=o["label"], callback_data=f"{CB_MY_DETAIL_PREFIX}{o['id']}")
        ])
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_service_detail(
    order_id: int, *, provisioned: bool, enabled: bool, is_test: bool = False
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if provisioned:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_VIEW_CONFIGS,
                callback_data=f"{CB_MY_CONFIGS_PREFIX}{order_id}",
            ),
        ])
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_REFRESH_USAGE,
                callback_data=f"{CB_MY_REFRESH_USAGE_PREFIX}{order_id}",
            ),
        ])
        if not is_test:
            toggle_text = texts.BTN_TOGGLE_OFF if enabled else texts.BTN_TOGGLE_ON
            rows.append([
                InlineKeyboardButton(
                    text=toggle_text, callback_data=f"{CB_MY_TOGGLE_PREFIX}{order_id}"
                ),
                InlineKeyboardButton(
                    text=texts.BTN_RENAME, callback_data=f"{CB_MY_RENAME_PREFIX}{order_id}"
                ),
            ])
            rows.append([
                InlineKeyboardButton(
                    text=texts.BTN_REGEN, callback_data=f"{CB_MY_REGEN_PREFIX}{order_id}"
                ),
            ])
    elif not is_test:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_RENAME, callback_data=f"{CB_MY_RENAME_PREFIX}{order_id}"
            ),
        ])
    rows.append([InlineKeyboardButton(text="🔙 لیست سرویس‌ها", callback_data=CB_MY_LIST)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_service(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🔙 جزئیات سرویس", callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}")
        ]]
    )


def regen_confirm(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_REGEN_CONFIRM,
                                     callback_data=f"{CB_MY_REGEN_CONFIRM_PREFIX}{order_id}"),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_BACK,
                                     callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}"),
            ],
        ]
    )


# ---------- admin reply keyboard ----------
def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=texts.ADMIN_BTN_DASHBOARD),
                KeyboardButton(text=texts.ADMIN_BTN_PENDING),
            ],
            [
                KeyboardButton(text=texts.ADMIN_BTN_SETTINGS),
                KeyboardButton(text=texts.ADMIN_BTN_LOCATIONS),
            ],
            [
                KeyboardButton(text=texts.ADMIN_BTN_TOOLS),
                KeyboardButton(text=texts.ADMIN_BTN_USERS),
            ],
            [KeyboardButton(text=texts.ADMIN_BTN_PANEL)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ---------- admin panel inline ----------
def admin_home_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_DASHBOARD, callback_data=CB_ADM_DASH
                ),
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_PENDING, callback_data=CB_ADM_PENDING_LIST
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_SETTINGS, callback_data=CB_ADM_SETTINGS
                ),
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_LOCATIONS, callback_data=CB_ADM_LOCATIONS_LIST
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_TOOLS, callback_data=CB_ADM_TOOLS
                ),
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_USERS, callback_data=CB_ADM_USERS
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_CMD_HELP_BTN, callback_data=CB_ADM_CMD_HELP
                ),
            ],
        ]
    )


def admin_dashboard_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_PENDING, callback_data=CB_ADM_PENDING_LIST
                ),
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_DASH
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.BTN_BACK, callback_data=CB_ADM_HOME
                ),
            ],
        ]
    )


def admin_settings_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 پلن‌های پایه",
                    callback_data=CB_ADM_PLANS,
                ),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME),
            ],
        ]
    )


def admin_plans_keyboard(
    volume_presets: list[int], duration_presets: list[int]
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for gb in volume_presets:
        rows.append([
            InlineKeyboardButton(
                text=f"❌ حذف {gb} GB",
                callback_data=f"{CB_ADM_VOL_DEL_PREFIX}{gb}",
            )
        ])
    for days in duration_presets:
        rows.append([
            InlineKeyboardButton(
                text=f"❌ حذف {days} روز",
                callback_data=f"{CB_ADM_DUR_DEL_PREFIX}{days}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_PLANS),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_SETTINGS),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_users_keyboard(
    users: list, *, page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """`users` — sqlite3.Row or dict with user_id, first_name, username."""
    rows: list[list[InlineKeyboardButton]] = []
    for u in users:
        uid = int(u["user_id"])
        label = (u["first_name"] or "").strip() or str(uid)
        if len(label) > 18:
            label = label[:17] + "…"
        rows.append([
            InlineKeyboardButton(
                text=f"👤 {label}",
                callback_data=f"{CB_ADM_USER_DETAIL_PREFIX}{uid}",
            )
        ])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀️ قبلی",
                callback_data=f"{CB_ADM_USERS_PAGE_PREFIX}{page - 1}",
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="بعدی ▶️",
                callback_data=f"{CB_ADM_USERS_PAGE_PREFIX}{page + 1}",
            )
        )
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton(text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_USERS),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_VIEW_USER,
                    url=f"tg://user?id={user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 لیست کاربران", callback_data=CB_ADM_USERS
                ),
            ],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_BROADCAST_SEND,
                    callback_data=CB_BROADCAST_CONFIRM,
                ),
                InlineKeyboardButton(
                    text=texts.BTN_BROADCAST_CANCEL,
                    callback_data=CB_BROADCAST_CANCEL,
                ),
            ],
        ]
    )


def broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_BROADCAST_CANCEL,
                    callback_data=CB_BROADCAST_CANCEL,
                ),
            ],
        ]
    )


def admin_tools_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_ADMIN_BROADCAST, callback_data=CB_ADM_BROADCAST
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 همگام‌سازی پنل", callback_data=CB_ADM_TOOL_SYNC
                ),
                InlineKeyboardButton(
                    text="🗑 پاکسازی رد/پرداخت‌نشده", callback_data=CB_ADM_TOOL_CLEAR
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_CMD_HELP_BTN, callback_data=CB_ADM_CMD_HELP
                ),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME),
            ],
        ]
    )


def admin_pending_list(orders: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for o in orders:
        rows.append([
            InlineKeyboardButton(
                text=o["label"],
                callback_data=f"{CB_ADM_ORDER_VIEW_PREFIX}{o['id']}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_PENDING_LIST),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_locations_list(locs: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locs:
        emoji = "🟢" if loc.enabled else "🔴"
        rows.append([
            InlineKeyboardButton(
                text=f"{emoji} #{loc.id} {loc.name}",
                callback_data=f"{CB_ADM_LOC_DETAIL_PREFIX}{loc.id}",
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_LOCATIONS_LIST
        ),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_location_detail(
    location_id: int, *, enabled: bool
) -> InlineKeyboardMarkup:
    toggle_label = "🔴 غیرفعال کردن" if enabled else "🟢 فعال کردن"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_label,
                    callback_data=f"{CB_ADM_LOC_TOGGLE_PREFIX}{location_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ حذف کامل لوکیشن",
                    callback_data=f"{CB_ADM_LOC_PURGE_PREFIX}{location_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 لیست لوکیشن‌ها", callback_data=CB_ADM_LOCATIONS_LIST
                ),
            ],
        ]
    )


# ---------- admin review ----------
def admin_review(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_ACCEPT, callback_data=f"{CB_ADMIN_ACCEPT_PREFIX}{order_id}"
                ),
                InlineKeyboardButton(
                    text=texts.BTN_DECLINE, callback_data=f"{CB_ADMIN_DECLINE_PREFIX}{order_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.BTN_VIEW_USER, url=f"tg://user?id={user_id}"
                )
            ],
        ]
    )
