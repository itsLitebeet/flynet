"""Configurable role → permission matrix (defaults + DB overrides)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.admin_perms import (
    ALL_PERMS,
    CUSTOMERS,
    DASHBOARD,
    LOCATIONS,
    MANAGE_ADMINS,
    OFFER,
    ORDERS_MANAGE,
    ORDERS_REVIEW,
    PANEL,
    ROLE_MANAGER,
    ROLE_OWNER,
    ROLE_REVIEWER,
    ROLE_SUPPORT,
    ROLE_VIEWER,
    SERVICES,
    SETTINGS,
    TOOLS_BROADCAST,
    TOOLS_MISC,
    TOOLS_SYNC,
    USERS,
    VALID_ROLES,
)

if TYPE_CHECKING:
    from app.db import Database

SETTING_ROLE_PERMISSIONS = "role_permissions_json"

# Built-in defaults (used when DB has no override for that role).
DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_MANAGER: frozenset({
        PANEL, DASHBOARD, ORDERS_REVIEW, ORDERS_MANAGE, USERS, CUSTOMERS,
        SETTINGS, SERVICES, OFFER, LOCATIONS,
        TOOLS_BROADCAST, TOOLS_SYNC, TOOLS_MISC,
    }),
    ROLE_REVIEWER: frozenset({
        PANEL, DASHBOARD, ORDERS_REVIEW, ORDERS_MANAGE, CUSTOMERS,
    }),
    ROLE_SUPPORT: frozenset({
        PANEL, DASHBOARD, ORDERS_REVIEW, USERS, CUSTOMERS,
    }),
    ROLE_VIEWER: frozenset({
        PANEL, DASHBOARD, USERS, CUSTOMERS,
    }),
}

CONFIGURABLE_ROLES: tuple[str, ...] = VALID_ROLES

# Matrix column order (owner row is always all ✅ in the UI).
MATRIX_ROLES: tuple[str, ...] = (
    ROLE_OWNER,
    ROLE_MANAGER,
    ROLE_REVIEWER,
    ROLE_SUPPORT,
    ROLE_VIEWER,
)

# Permissions shown in the owner matrix (manage_admins is owner-only, not toggled).
TOGGLABLE_PERMS: tuple[str, ...] = tuple(
    p for p in (
        PANEL,
        DASHBOARD,
        ORDERS_REVIEW,
        ORDERS_MANAGE,
        USERS,
        CUSTOMERS,
        SETTINGS,
        SERVICES,
        OFFER,
        LOCATIONS,
        TOOLS_BROADCAST,
        TOOLS_SYNC,
        TOOLS_MISC,
    )
)

PERM_LABELS: dict[str, str] = {
    PANEL: "panel",
    DASHBOARD: "dashboard",
    ORDERS_REVIEW: "orders_review",
    ORDERS_MANAGE: "orders_manage",
    USERS: "users",
    CUSTOMERS: "customers",
    SETTINGS: "settings",
    SERVICES: "services",
    OFFER: "offer",
    LOCATIONS: "locations",
    TOOLS_BROADCAST: "tools_broadcast",
    TOOLS_SYNC: "tools_sync",
    TOOLS_MISC: "tools_misc",
    MANAGE_ADMINS: "manage_admins",
}

ROLE_SHORT_LABELS: dict[str, str] = {
    ROLE_OWNER: "Owner",
    ROLE_MANAGER: "Manager",
    ROLE_REVIEWER: "Reviewer",
    ROLE_SUPPORT: "Support",
    ROLE_VIEWER: "Viewer",
}


async def _load_matrix(db: Database) -> dict[str, list[str]]:
    import json

    raw = await db.get_setting(SETTING_ROLE_PERMISSIONS, "{}") or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[str]] = {}
    for role, perms in data.items():
        if role not in CONFIGURABLE_ROLES or not isinstance(perms, list):
            continue
        out[str(role)] = [p for p in perms if p in ALL_PERMS and p != MANAGE_ADMINS]
    return out


async def _save_matrix(db: Database, matrix: dict[str, list[str]]) -> None:
    import json

    await db.set_setting(SETTING_ROLE_PERMISSIONS, json.dumps(matrix, ensure_ascii=False))


async def permissions_for_role(db: Database, role: str) -> frozenset[str]:
    if role == ROLE_OWNER:
        return ALL_PERMS
    stored = (await _load_matrix(db)).get(role)
    if stored is not None:
        perms = frozenset(stored)
        if not perms:
            return DEFAULT_ROLE_PERMISSIONS.get(
                role, DEFAULT_ROLE_PERMISSIONS[ROLE_VIEWER]
            )
        if PANEL not in perms:
            perms = perms | frozenset({PANEL})
        return perms
    return DEFAULT_ROLE_PERMISSIONS.get(
        role, DEFAULT_ROLE_PERMISSIONS[ROLE_VIEWER]
    )


async def role_has_custom_permissions(db: Database, role: str) -> bool:
    return role in (await _load_matrix(db))


async def set_role_permissions(db: Database, role: str, perms: set[str] | frozenset[str]) -> None:
    if role not in CONFIGURABLE_ROLES:
        raise ValueError("invalid role")
    clean = {p for p in perms if p in TOGGLABLE_PERMS}
    if PANEL not in clean:
        clean.add(PANEL)
    matrix = await _load_matrix(db)
    matrix[role] = sorted(clean)
    await _save_matrix(db, matrix)


async def toggle_role_permission(db: Database, role: str, perm: str) -> bool:
    if role not in CONFIGURABLE_ROLES or perm not in TOGGLABLE_PERMS:
        raise ValueError("invalid role or permission")
    if perm == PANEL and perm in (await permissions_for_role(db, role)):
        raise ValueError("panel is required")
    current = set(await permissions_for_role(db, role))
    if perm in current:
        current.discard(perm)
    else:
        current.add(perm)
    current.add(PANEL)
    await set_role_permissions(db, role, current)
    return perm in current


async def reset_role_permissions(db: Database, role: str) -> None:
    if role not in CONFIGURABLE_ROLES:
        raise ValueError("invalid role")
    matrix = await _load_matrix(db)
    matrix.pop(role, None)
    await _save_matrix(db, matrix)


async def reset_all_role_permissions(db: Database) -> None:
    await _save_matrix(db, {})


def _mark(enabled: bool) -> str:
    return "✅" if enabled else "❌"


async def format_full_matrix_text(db: Database) -> str:
    from app import texts

    col_width = 14
    left_padding = 16

    header = "Permission".ljust(left_padding)
    for role in MATRIX_ROLES:
        header += ROLE_SHORT_LABELS[role].center(col_width)
    lines = [f"<pre>{header}"]

    pad_left = (col_width - 2) // 2
    pad_right = col_width - 2 - pad_left

    for perm in TOGGLABLE_PERMS:
        row = PERM_LABELS.get(perm, perm).ljust(left_padding)
        for role in MATRIX_ROLES:
            if role == ROLE_OWNER:
                on = True
            else:
                on = perm in (await permissions_for_role(db, role))
            row += " " * pad_left + _mark(on) + " " * pad_right
        lines.append(row)

    lines.append("manage_admins".ljust(left_padding) + "".join(
        " " * pad_left + _mark(r == ROLE_OWNER) + " " * pad_right for r in MATRIX_ROLES
    ))
    lines.append("</pre>")
    lines.append(texts.ADMIN_PERM_MATRIX_HINT)
    return "\n".join(lines)


async def format_role_editor_text(db: Database, role: str) -> str:
    from app import texts

    from app.texts import ADMIN_ROLE_LABELS

    label = ADMIN_ROLE_LABELS.get(role, role)
    custom = " (سفارشی)" if (await role_has_custom_permissions(db, role)) else " (پیش‌فرض)"
    lines = [texts.ADMIN_PERM_ROLE_HEADER.format(role_label=label, custom=custom), ""]
    for perm in TOGGLABLE_PERMS:
        on = perm in (await permissions_for_role(db, role))
        lines.append(f"{PERM_LABELS[perm]} — {_mark(on)}")
    return "\n".join(lines)
