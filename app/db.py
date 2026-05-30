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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    base_url    TEXT NOT NULL,
    api_token   TEXT NOT NULL,
    inbound_ids TEXT NOT NULL,      -- JSON array of integers
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
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


@dataclass(frozen=True)
class Location:
    id: int
    name: str
    base_url: str
    api_token: str
    inbound_ids: list[int]
    enabled: bool


def _row_to_location(row: sqlite3.Row) -> Location:
    try:
        inbound_ids = json.loads(row["inbound_ids"])
        if not isinstance(inbound_ids, list):
            inbound_ids = []
    except (json.JSONDecodeError, TypeError):
        inbound_ids = []
    return Location(
        id=int(row["id"]),
        name=str(row["name"]),
        base_url=str(row["base_url"]),
        api_token=str(row["api_token"]),
        inbound_ids=[int(x) for x in inbound_ids],
        enabled=bool(row["enabled"]),
    )


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path) if not str(path).startswith(":") else path  # ":memory:"
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._seed_defaults()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def _seed_defaults(self) -> None:
        with self._cursor() as cur:
            for k, v in DEFAULT_SETTINGS.items():
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
        """Returns (base, per_gb, per_day) in toman."""
        return (
            self.get_int_setting("price_base", 0),
            self.get_int_setting("price_per_gb", 0),
            self.get_int_setting("price_per_day", 0),
        )

    # ---------- locations ----------
    def add_location(
        self, name: str, base_url: str, api_token: str, inbound_ids: list[int]
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO locations (name, base_url, api_token, inbound_ids) "
                "VALUES (?, ?, ?, ?)",
                (name, base_url, api_token, json.dumps(inbound_ids)),
            )
            return int(cur.lastrowid or 0)

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

    def get_location(self, location_id: int) -> Location | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
            row = cur.fetchone()
            return _row_to_location(row) if row else None

    def list_locations(self, only_enabled: bool = False) -> list[Location]:
        with self._cursor() as cur:
            if only_enabled:
                cur.execute("SELECT * FROM locations WHERE enabled = 1 ORDER BY id")
            else:
                cur.execute("SELECT * FROM locations ORDER BY id")
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
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO orders "
                "(user_id, location_id, location_name, volume_gb, duration_days, price) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, location_id, location_name, volume_gb, duration_days, price),
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
