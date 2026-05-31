from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    last_name  TEXT,
    lang_code  TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_banned  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    base_url          TEXT NOT NULL,
    api_token         TEXT NOT NULL,
    inbound_ids       TEXT NOT NULL,      -- JSON array of integers
    sub_url_template  TEXT,                -- e.g. https://host:2096/sub/{subId}
    price_base        INTEGER,             -- NULL = use global default from settings
    price_per_gb      INTEGER,
    price_per_day     INTEGER,
    enabled           INTEGER NOT NULL DEFAULT 1,
    is_test           INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    location_id         INTEGER NOT NULL,
    location_name       TEXT    NOT NULL,        -- snapshot in case location is deleted
    volume_gb           INTEGER NOT NULL,
    duration_days       INTEGER NOT NULL,
    price               INTEGER NOT NULL,        -- toman
    status              TEXT    NOT NULL DEFAULT 'awaiting_payment',
                                                 -- awaiting_payment | awaiting_review
                                                 -- | approved | declined
                                                 -- | provisioned | failed
    screenshot_file_id  TEXT,
    admin_id            INTEGER,                 -- who reviewed
    decline_reason      TEXT,
    xui_email           TEXT,
    xui_sub_id          TEXT,
    xui_client_uuid     TEXT,
    sub_links           TEXT,                    -- JSON array of strings
    nickname            TEXT,                    -- user-chosen local nickname
    is_test             INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)     REFERENCES users(user_id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS tickets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    message    TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'open',
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


# Defaults seeded into the settings table on first run.
DEFAULT_SETTINGS: dict[str, str] = {
    "card_number":   "6037-9912-3456-7890",
    "card_holder":   "NetFly",
    "price_base":    "20000",   # toman, flat per order
    "price_per_gb":  "8000",    # toman per GB
    "price_per_day": "1500",    # toman per day
}

# JSON lists in settings — seeded from app.texts defaults on first run.
SETTING_VOLUME_PRESETS = "volume_presets_gb"
SETTING_DURATION_PRESETS = "duration_presets_days"
SETTING_TEST_ENABLED = "test_feature_enabled"
MAX_PLAN_PRESETS = 12
TEST_VOLUME_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class Location:
    id: int
    name: str
    base_url: str
    api_token: str
    inbound_ids: list[int]
    sub_url_template: str | None
    price_base: int | None
    price_per_gb: int | None
    price_per_day: int | None
    enabled: bool
    is_test: bool

    def render_sub_url(self, sub_id: str | None) -> str | None:
        if not self.sub_url_template or not sub_id:
            return None
        return self.sub_url_template.replace("{subId}", sub_id)


def _row_to_location(row: sqlite3.Row) -> Location:
    try:
        inbound_ids = json.loads(row["inbound_ids"])
        if not isinstance(inbound_ids, list):
            inbound_ids = []
    except (json.JSONDecodeError, TypeError):
        inbound_ids = []
    # sub_url_template may be missing from older rows; .keys() is safe via Row.
    sub_url_template = None
    try:
        sub_url_template = row["sub_url_template"]
    except (IndexError, KeyError):
        pass
    def _opt_int(key: str) -> int | None:
        try:
            v = row[key]
            return int(v) if v is not None else None
        except (IndexError, KeyError, TypeError, ValueError):
            return None

    return Location(
        id=int(row["id"]),
        name=str(row["name"]),
        base_url=str(row["base_url"]),
        api_token=str(row["api_token"]),
        inbound_ids=[int(x) for x in inbound_ids],
        sub_url_template=str(sub_url_template) if sub_url_template else None,
        price_base=_opt_int("price_base"),
        price_per_gb=_opt_int("price_per_gb"),
        price_per_day=_opt_int("price_per_day"),
        enabled=bool(row["enabled"]),
        is_test=bool(row["is_test"]) if "is_test" in row.keys() else False,
    )


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path) if not str(path).startswith(":") else path  # ":memory:"
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._migrate()
        self._seed_defaults()
        self._backfill_location_pricing()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def _ensure_column(self, table: str, column: str, sql_type: str) -> None:
        """Idempotently add a column to `table` if it isn't already there."""
        with self._cursor() as cur:
            cur.execute(f"PRAGMA table_info({table})")
            cols = {row["name"] for row in cur.fetchall()}
            if column not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")

    def _migrate(self) -> None:
        """Schema migrations for upgrades from earlier versions of this bot.

        Each step must be safe to re-run (idempotent) and avoid destructive
        changes. SQLite's ALTER TABLE only supports add-column, so we stick
        to additive evolution.
        """
        self._ensure_column("locations", "sub_url_template", "TEXT")
        self._ensure_column("locations", "price_base", "INTEGER")
        self._ensure_column("locations", "price_per_gb", "INTEGER")
        self._ensure_column("locations", "price_per_day", "INTEGER")
        self._ensure_column("orders", "nickname", "TEXT")
        self._ensure_column("orders", "admin_receipt_refs", "TEXT")
        self._ensure_column("locations", "is_test", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("orders", "is_test", "INTEGER NOT NULL DEFAULT 0")
        # Legacy status from an earlier version — hard-delete on upgrade.
        with self._cursor() as cur:
            cur.execute("DELETE FROM orders WHERE status = 'panel_removed'")
        # Base buy plans (volume/duration buttons) — seed if missing on upgrade.
        from app import texts

        plan_defaults = {
            SETTING_VOLUME_PRESETS: json.dumps(texts.DEFAULT_VOLUME_PRESETS_GB),
            SETTING_DURATION_PRESETS: json.dumps(texts.DEFAULT_DURATION_PRESETS_DAYS),
        }
        with self._cursor() as cur:
            for k, v in plan_defaults.items():
                cur.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (k, v),
                )

    def _backfill_location_pricing(self) -> None:
        base, per_gb, per_day = self.get_pricing()
        with self._cursor() as cur:
            cur.execute(
                "UPDATE locations SET price_base = ?, price_per_gb = ?, price_per_day = ? "
                "WHERE price_base IS NULL",
                (base, per_gb, per_day),
            )

    def _seed_defaults(self) -> None:
        from app import texts

        extras = {
            SETTING_VOLUME_PRESETS: json.dumps(texts.DEFAULT_VOLUME_PRESETS_GB),
            SETTING_DURATION_PRESETS: json.dumps(texts.DEFAULT_DURATION_PRESETS_DAYS),
            SETTING_TEST_ENABLED: "0",
        }
        with self._cursor() as cur:
            for k, v in {**DEFAULT_SETTINGS, **extras}.items():
                cur.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (k, v),
                )

    # ---------- users ----------
    def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        lang_code: str | None,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name, lang_code)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username   = excluded.username,
                    first_name = excluded.first_name,
                    last_name  = excluded.last_name,
                    lang_code  = excluded.lang_code
                """,
                (user_id, username, first_name, last_name, lang_code),
            )

    def is_banned(self, user_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return bool(row and row["is_banned"])

    def count_users(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users")
            return int(cur.fetchone()["c"])

    def all_user_ids(self) -> list[int]:
        with self._cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE is_banned = 0")
            return [int(r["user_id"]) for r in cur.fetchall()]

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cur.fetchone()

    def recent_users(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT user_id, username, first_name, created_at "
                "FROM users ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return list(cur.fetchall())

    def list_users_paginated(self, offset: int, limit: int) -> list[sqlite3.Row]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return list(cur.fetchall())

    def list_user_orders_admin(
        self, user_id: int, limit: int = 30
    ) -> list[sqlite3.Row]:
        """All orders for a user (admin view), newest first."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, status, xui_email, location_name, volume_gb, "
                "duration_days, nickname, price, created_at, updated_at "
                "FROM orders WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            )
            return list(cur.fetchall())

    # ---------- settings (key/value) ----------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_int_setting(self, key: str, default: int) -> int:
        raw = self.get_setting(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def get_pricing(self) -> tuple[int, int, int]:
        """Global default pricing (base, per_gb, per_day) in toman."""
        return (
            self.get_int_setting("price_base", 0),
            self.get_int_setting("price_per_gb", 0),
            self.get_int_setting("price_per_day", 0),
        )

    def _get_int_list_setting(self, key: str, fallback: list[int]) -> list[int]:
        raw = self.get_setting(key)
        if not raw:
            return list(fallback)
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                return list(fallback)
            out = sorted({int(x) for x in data if int(x) > 0})
            return out if out else list(fallback)
        except (json.JSONDecodeError, TypeError, ValueError):
            return list(fallback)

    def _set_int_list_setting(self, key: str, values: list[int]) -> None:
        clean = sorted({int(v) for v in values if int(v) > 0})
        self.set_setting(key, json.dumps(clean))

    def get_volume_presets(self) -> list[int]:
        from app import texts

        return self._get_int_list_setting(
            SETTING_VOLUME_PRESETS, texts.DEFAULT_VOLUME_PRESETS_GB
        )

    def get_duration_presets(self) -> list[int]:
        from app import texts

        return self._get_int_list_setting(
            SETTING_DURATION_PRESETS, texts.DEFAULT_DURATION_PRESETS_DAYS
        )

    def add_volume_preset(self, gb: int) -> tuple[bool, str]:
        if gb < 1 or gb > 500:
            return False, "invalid"
        presets = self.get_volume_presets()
        if gb in presets:
            return False, "exists"
        if len(presets) >= MAX_PLAN_PRESETS:
            return False, "max"
        presets.append(gb)
        self._set_int_list_setting(SETTING_VOLUME_PRESETS, presets)
        return True, "ok"

    def remove_volume_preset(self, gb: int) -> tuple[bool, str]:
        presets = self.get_volume_presets()
        if gb not in presets:
            return False, "missing"
        if len(presets) <= 1:
            return False, "last"
        presets.remove(gb)
        self._set_int_list_setting(SETTING_VOLUME_PRESETS, presets)
        return True, "ok"

    def add_duration_preset(self, days: int) -> tuple[bool, str]:
        if days < 1 or days > 3650:
            return False, "invalid"
        presets = self.get_duration_presets()
        if days in presets:
            return False, "exists"
        if len(presets) >= MAX_PLAN_PRESETS:
            return False, "max"
        presets.append(days)
        self._set_int_list_setting(SETTING_DURATION_PRESETS, presets)
        return True, "ok"

    def remove_duration_preset(self, days: int) -> tuple[bool, str]:
        presets = self.get_duration_presets()
        if days not in presets:
            return False, "missing"
        if len(presets) <= 1:
            return False, "last"
        presets.remove(days)
        self._set_int_list_setting(SETTING_DURATION_PRESETS, presets)
        return True, "ok"

    def get_pricing_for_location(self, location_id: int) -> tuple[int, int, int]:
        """Resolved pricing for a location (custom or global fallback per field)."""
        g_base, g_per_gb, g_per_day = self.get_pricing()
        loc = self.get_location(location_id)
        if loc is None:
            return g_base, g_per_gb, g_per_day
        return (
            loc.price_base if loc.price_base is not None else g_base,
            loc.price_per_gb if loc.price_per_gb is not None else g_per_gb,
            loc.price_per_day if loc.price_per_day is not None else g_per_day,
        )

    # ---------- locations ----------
    def add_location(
        self,
        name: str,
        base_url: str,
        api_token: str,
        inbound_ids: list[int],
        sub_url_template: str | None = None,
        *,
        price_base: int | None = None,
        price_per_gb: int | None = None,
        price_per_day: int | None = None,
        is_test: bool = False,
    ) -> int:
        if price_base is None:
            price_base, price_per_gb, price_per_day = self.get_pricing()
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO locations "
                "(name, base_url, api_token, inbound_ids, sub_url_template, "
                "price_base, price_per_gb, price_per_day, is_test) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    base_url,
                    api_token,
                    json.dumps(inbound_ids),
                    sub_url_template,
                    price_base,
                    price_per_gb,
                    price_per_day,
                    1 if is_test else 0,
                ),
            )
            return int(cur.lastrowid or 0)

    def replace_test_location(
        self,
        *,
        name: str,
        base_url: str,
        api_token: str,
        inbound_ids: list[int],
        sub_url_template: str | None = None,
    ) -> int:
        """Disable or remove the previous test location, then insert the new one."""
        with self._cursor() as cur:
            cur.execute("SELECT id FROM locations WHERE is_test = 1")
            for row in cur.fetchall():
                old_id = int(row["id"])
                cur.execute(
                    "SELECT COUNT(*) AS c FROM orders WHERE location_id = ?",
                    (old_id,),
                )
                if int(cur.fetchone()["c"]) > 0:
                    cur.execute(
                        "UPDATE locations SET enabled = 0 WHERE id = ?", (old_id,)
                    )
                else:
                    cur.execute("DELETE FROM locations WHERE id = ?", (old_id,))
        return self.add_location(
            name=name,
            base_url=base_url,
            api_token=api_token,
            inbound_ids=inbound_ids,
            sub_url_template=sub_url_template,
            price_base=0,
            price_per_gb=0,
            price_per_day=0,
            is_test=True,
        )

    def get_test_location(self) -> Location | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM locations WHERE is_test = 1 AND enabled = 1 "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            return _row_to_location(row) if row else None

    def is_test_feature_enabled(self) -> bool:
        return self.get_setting(SETTING_TEST_ENABLED, "0") == "1"

    def set_test_feature_enabled(self, enabled: bool) -> None:
        self.set_setting(SETTING_TEST_ENABLED, "1" if enabled else "0")

    def user_has_claimed_test(self, user_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM orders WHERE user_id = ? AND is_test = 1 "
                "AND status != 'declined' LIMIT 1",
                (user_id,),
            )
            return cur.fetchone() is not None

    def set_location_pricing(
        self,
        location_id: int,
        *,
        price_base: int | None,
        price_per_gb: int | None,
        price_per_day: int | None,
    ) -> bool:
        """Set custom pricing. Pass all None to revert to global defaults."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE locations SET price_base = ?, price_per_gb = ?, price_per_day = ? "
                "WHERE id = ?",
                (price_base, price_per_gb, price_per_day, location_id),
            )
            return cur.rowcount > 0

    def set_location_sub_url_template(
        self, location_id: int, template: str | None
    ) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE locations SET sub_url_template = ? WHERE id = ?",
                (template, location_id),
            )
            return cur.rowcount > 0

    def remove_location(self, location_id: int) -> str:
        """Hard-delete a location, or disable it if orders still reference it.

        Returns one of:
          - 'not_found' — no such location
          - 'deleted'   — removed from the DB (no orders referenced it)
          - 'disabled'  — kept in DB but marked enabled=0 (orders depend on it)

        We never break the FK because the admin review flow looks up the
        location's panel credentials when provisioning an Accept'd order,
        so silently dropping the row would brick any pending orders.
        """
        with self._cursor() as cur:
            cur.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
            if cur.fetchone() is None:
                return "not_found"
            cur.execute(
                "SELECT COUNT(*) AS c FROM orders WHERE location_id = ?",
                (location_id,),
            )
            has_orders = int(cur.fetchone()["c"]) > 0
            if has_orders:
                cur.execute(
                    "UPDATE locations SET enabled = 0 WHERE id = ?", (location_id,)
                )
                return "disabled"
            cur.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            return "deleted"

    def set_location_enabled(self, location_id: int, enabled: bool) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE locations SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, location_id),
            )
            return cur.rowcount > 0

    def count_orders_for_location(self, location_id: int) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM orders WHERE location_id = ?",
                (location_id,),
            )
            return int(cur.fetchone()["c"])

    def purge_location(self, location_id: int) -> str:
        """Hard-delete a location AND every order that references it.

        Returns 'not_found' or 'purged'. Use this only when you're sure you
        want to lose the order history. Wrapped in a single transaction so a
        crash mid-purge leaves the DB consistent.
        """
        with self._cursor() as cur:
            cur.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
            if cur.fetchone() is None:
                return "not_found"
            cur.execute("DELETE FROM orders   WHERE location_id = ?", (location_id,))
            cur.execute("DELETE FROM locations WHERE id = ?",           (location_id,))
            return "purged"

    def get_location(self, location_id: int) -> Location | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
            row = cur.fetchone()
            return _row_to_location(row) if row else None

    def list_locations(
        self,
        only_enabled: bool = False,
        *,
        exclude_test: bool = False,
        only_test: bool = False,
    ) -> list[Location]:
        clauses: list[str] = []
        if only_enabled:
            clauses.append("enabled = 1")
        if exclude_test:
            clauses.append("is_test = 0")
        if only_test:
            clauses.append("is_test = 1")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._cursor() as cur:
            cur.execute(f"SELECT * FROM locations {where} ORDER BY id")
            return [_row_to_location(r) for r in cur.fetchall()]

    # ---------- orders ----------
    def create_order(
        self,
        user_id: int,
        location_id: int,
        location_name: str,
        volume_gb: int,
        duration_days: int,
        price: int,
        *,
        is_test: bool = False,
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO orders "
                "(user_id, location_id, location_name, volume_gb, duration_days, price, "
                "is_test) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    location_id,
                    location_name,
                    volume_gb,
                    duration_days,
                    price,
                    1 if is_test else 0,
                ),
            )
            return int(cur.lastrowid or 0)

    def set_order_screenshot(
        self, order_id: int, file_id: str, new_status: str = "awaiting_review"
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET screenshot_file_id = ?, status = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (file_id, new_status, order_id),
            )

    def set_order_status(
        self,
        order_id: int,
        status: str,
        admin_id: int | None = None,
        decline_reason: str | None = None,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = ?, admin_id = COALESCE(?, admin_id), "
                "decline_reason = COALESCE(?, decline_reason), "
                "updated_at = datetime('now') WHERE id = ?",
                (status, admin_id, decline_reason, order_id),
            )

    def claim_order_review(
        self,
        order_id: int,
        status: str,
        admin_id: int,
        *,
        decline_reason: str | None = None,
    ) -> bool:
        """Atomically move order from awaiting_review → status (one admin wins)."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = ?, admin_id = ?, "
                "decline_reason = COALESCE(?, decline_reason), "
                "updated_at = datetime('now') "
                "WHERE id = ? AND status = 'awaiting_review'",
                (status, admin_id, decline_reason, order_id),
            )
            return cur.rowcount > 0

    def add_admin_receipt_message(
        self, order_id: int, admin_id: int, message_id: int
    ) -> None:
        """Remember each admin's receipt message so buttons can be cleared later."""
        order = self.get_order(order_id)
        refs: dict[str, int] = {}
        if order is not None:
            raw = order["admin_receipt_refs"]
            if raw:
                try:
                    loaded = json.loads(raw)
                    if isinstance(loaded, dict):
                        refs = {str(k): int(v) for k, v in loaded.items()}
                except (json.JSONDecodeError, TypeError, ValueError):
                    refs = {}
        refs[str(admin_id)] = message_id
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET admin_receipt_refs = ? WHERE id = ?",
                (json.dumps(refs), order_id),
            )

    def get_admin_receipt_refs(self, order_id: int) -> dict[int, int]:
        order = self.get_order(order_id)
        if order is None:
            return {}
        raw = order["admin_receipt_refs"]
        if not raw:
            return {}
        try:
            loaded = json.loads(raw)
            if not isinstance(loaded, dict):
                return {}
            return {int(k): int(v) for k, v in loaded.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

    def set_order_provisioned(
        self,
        order_id: int,
        email: str,
        sub_id: str | None,
        client_uuid: str | None,
        sub_links: list[str],
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = 'provisioned', xui_email = ?, "
                "xui_sub_id = ?, xui_client_uuid = ?, sub_links = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (email, sub_id, client_uuid, json.dumps(sub_links), order_id),
            )

    def get_order(self, order_id: int) -> sqlite3.Row | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            return cur.fetchone()

    def list_user_orders(self, user_id: int, limit: int = 50) -> list[sqlite3.Row]:
        """Orders visible to the buyer in «سرویس‌های من».

        Hides declined orders (buyers should not see rejected purchases).
        """
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE user_id = ? "
                "AND status != 'declined' "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
            return list(cur.fetchall())

    def set_order_nickname(self, order_id: int, nickname: str | None) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET nickname = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (nickname, order_id),
            )
            return cur.rowcount > 0

    def update_order_xui(
        self,
        order_id: int,
        *,
        email: str,
        sub_id: str | None,
        client_uuid: str | None,
        sub_links: list[str],
    ) -> None:
        """Used by the regenerate flow when a new panel client replaces the old one."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET xui_email = ?, xui_sub_id = ?, "
                "xui_client_uuid = ?, sub_links = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (email, sub_id, client_uuid, json.dumps(sub_links), order_id),
            )

    def count_orders(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM orders")
            return int(cur.fetchone()["c"])

    def count_orders_by_status(self, status: str) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM orders WHERE status = ?", (status,))
            return int(cur.fetchone()["c"])

    def pending_orders(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE status = 'awaiting_review' "
                "ORDER BY created_at ASC LIMIT ?",
                (limit,),
            )
            return list(cur.fetchall())

    def list_provisioned_orders(
        self, location_id: int | None = None
    ) -> list[sqlite3.Row]:
        """All orders still marked provisioned (optionally for one location)."""
        with self._cursor() as cur:
            if location_id is not None:
                cur.execute(
                    "SELECT * FROM orders WHERE status = 'provisioned' "
                    "AND location_id = ? ORDER BY id",
                    (location_id,),
                )
            else:
                cur.execute(
                    "SELECT * FROM orders WHERE status = 'provisioned' ORDER BY id"
                )
            return list(cur.fetchall())

    def delete_order(self, order_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            return cur.rowcount > 0

    def delete_orders_by_status(self, status: str) -> int:
        with self._cursor() as cur:
            cur.execute("DELETE FROM orders WHERE status = ?", (status,))
            return cur.rowcount

    # ---------- tickets ----------
    def create_ticket(self, user_id: int, message: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO tickets (user_id, message) VALUES (?, ?)",
                (user_id, message),
            )
            return int(cur.lastrowid or 0)

    def count_tickets(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM tickets")
            return int(cur.fetchone()["c"])

    def close(self) -> None:
        self._conn.close()
