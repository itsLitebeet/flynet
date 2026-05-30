from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from app import texts
from app.db import Database


class UserMiddleware(BaseMiddleware):
    """Auto-register every Telegram user we see, and short-circuit banned users.

    Also injects the `Database` instance into handler data so handlers can use
    `db: Database` as a parameter.
    """

    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")

        if tg_user is not None and not tg_user.is_bot:
            self.db.upsert_user(
                user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                lang_code=tg_user.language_code,
            )

            if self.db.is_banned(tg_user.id):
                if isinstance(event, Message):
                    await event.answer(texts.USER_BANNED)
                elif isinstance(event, CallbackQuery):
                    await event.answer(texts.USER_BANNED, show_alert=True)
                return None

        data["db"] = self.db
        return await handler(event, data)
