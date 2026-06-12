from __future__ import annotations

import json
from typing import Any
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

class SQLiteFSMStorage(BaseStorage):
    def __init__(self, db) -> None:
        self.db = db

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_str = state.state if hasattr(state, "state") else (str(state) if state is not None else None)
        async with self.db._cursor() as cur:
            await cur.execute(
                """
                INSERT INTO fsm_storage (bot_id, chat_id, user_id, state, data)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(bot_id, chat_id, user_id) DO UPDATE SET state = excluded.state
                """,
                (key.bot_id, key.chat_id, key.user_id, state_str, "{}"),
            )

    async def get_state(self, key: StorageKey) -> str | None:
        async with self.db._cursor() as cur:
            await cur.execute(
                "SELECT state FROM fsm_storage WHERE bot_id = ? AND chat_id = ? AND user_id = ?",
                (key.bot_id, key.chat_id, key.user_id),
            )
            row = await cur.fetchone()
            return row["state"] if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        data_str = json.dumps(data, ensure_ascii=False)
        async with self.db._cursor() as cur:
            await cur.execute(
                """
                INSERT INTO fsm_storage (bot_id, chat_id, user_id, state, data)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(bot_id, chat_id, user_id) DO UPDATE SET data = excluded.data
                """,
                (key.bot_id, key.chat_id, key.user_id, None, data_str),
            )

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self.db._cursor() as cur:
            await cur.execute(
                "SELECT data FROM fsm_storage WHERE bot_id = ? AND chat_id = ? AND user_id = ?",
                (key.bot_id, key.chat_id, key.user_id),
            )
            row = await cur.fetchone()
            if row and row["data"]:
                try:
                    return json.loads(row["data"])
                except Exception:
                    return {}
            return {}

    async def close(self) -> None:
        pass
