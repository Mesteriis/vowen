"""Trusted Telegram adapter. Never exposes approval through the public API."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    TelegramObject,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.crypto import PayloadCipher
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.auth.android_challenge import decide_challenge, present_challenge
from vowen.modules.forms.delivery import deliver_one
from vowen.modules.forms.models import BotContact
from vowen.modules.identity.models import User
from vowen.modules.notifications.delivery import deliver_one as deliver_member
from vowen.modules.notifications.delivery import suppress_recipient


class BotThrottle(BaseMiddleware):
    def __init__(self) -> None:
        self.windows: dict[int, tuple[float, int]] = {}
        self.sweep = 0.0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        actor = event.from_user if isinstance(event, (Message, CallbackQuery)) else None
        if actor is None:
            return await handler(event, data)
        now = time.monotonic()
        if now - self.sweep > 60:
            self.windows = {
                key: value for key, value in self.windows.items() if now - value[0] < 60
            }
            self.sweep = now
        start, count = self.windows.get(actor.id, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        if count >= 30 or (actor.id not in self.windows and len(self.windows) >= 10000):
            if isinstance(event, CallbackQuery):
                await event.answer("Too many attempts")
            return None
        self.windows[actor.id] = (start, count + 1)
        return await handler(event, data)


def build_router(settings: Settings) -> Router:
    engine = engine_for(settings.database_url)
    sessions = sessions_for(engine)
    router = Router()
    throttle = BotThrottle()
    router.message.outer_middleware(throttle)
    router.callback_query.outer_middleware(throttle)

    @router.message(Command("notifications_on", "notifications_off"))
    async def contact_preferences(message: Message) -> None:
        if message.chat.type != "private" or message.from_user is None:
            return
        async with sessions() as db, db.begin():
            contact = await db.get(BotContact, message.from_user.id, with_for_update=True)
            if contact is None:
                contact = BotContact(telegram_id=message.from_user.id)
                db.add(contact)
            contact.allowed = (message.text or "").split("@")[0] == "/notifications_on"
            if not contact.allowed:
                contact.delivery_generation = (contact.delivery_generation or 0) + 1
                uid = await db.scalar(
                    select(User.id).where(User.telegram_id == contact.telegram_id)
                )
                if uid:
                    await suppress_recipient(db, uid)
        await message.answer("Notification preference saved / Настройка уведомлений сохранена")

    @router.message(CommandStart())
    async def start(message: Message, command: CommandObject) -> None:
        if message.chat.type != "private" or message.from_user is None:
            return
        payload = command.args or ""
        if not payload.startswith("login_") or len(payload) != 49:
            await message.answer(
                "Open your instance to sign in. / Откройте свой инстанс для входа."
            )
            return
        try:
            async with sessions() as db, db.begin():
                challenge = await present_challenge(
                    db, payload[6:], message.from_user.id, Clock().now()
                )
                challenge_id, code, device = (
                    challenge.id,
                    challenge.display_code,
                    challenge.device_label,
                )
        except AppError:
            await message.answer("Access denied or expired. / Доступ запрещён или срок истёк.")
            return
        # No DB transaction is held while sending to Telegram. Plain text; no HTML parse mode.
        await message.answer(
            f"{settings.app_display_name}\n{settings.public_base_url}\n"
            f"{device}\nCode / Код: {code}\n"
            "Approve only your own initiated login with the matching code.\n"
            "Подтверждайте только начатый вами вход с совпадающим кодом.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Confirm / Подтвердить", callback_data=f"login:y:{challenge_id}"
                        ),
                        InlineKeyboardButton(
                            text="Reject / Отклонить", callback_data=f"login:n:{challenge_id}"
                        ),
                    ]
                ]
            ),
        )

    @router.callback_query(F.data.startswith("login:"))
    async def confirm(callback: CallbackQuery) -> None:
        if not isinstance(callback.message, Message) or callback.message.chat.type != "private":
            await callback.answer("Access denied")
            return
        try:
            prefix, decision, raw_id = (callback.data or "").split(":")
            if prefix != "login" or decision not in ("y", "n"):
                raise ValueError
            async with sessions() as db, db.begin():
                await decide_challenge(
                    db, UUID(raw_id), callback.from_user.id, decision == "y", Clock().now()
                )
        except (AppError, ValueError):
            await callback.answer("Access denied or expired", show_alert=True)
            return
        await callback.answer("Confirmed" if decision == "y" else "Rejected")
        await callback.message.edit_reply_markup(reply_markup=None)

    async def shutdown() -> None:
        await engine.dispose()

    router.shutdown.register(shutdown)
    return router


async def deliver_updates(
    sessions: async_sessionmaker[AsyncSession],
    keyring: Path,
    bot: Bot,
    base_url: str,
) -> None:
    async def send(chat_id: int, text: str) -> None:
        await bot.send_message(
            chat_id,
            text,
            parse_mode=None,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            request_timeout=30,
        )

    # A form delivery failure must not starve the independent member queue.
    try:
        await deliver_one(sessions, PayloadCipher(keyring), send)
    except Exception:
        logging.getLogger("vowen").warning("Form notification delivery unavailable")
    try:
        await deliver_member(sessions, base_url, send)
    except Exception:
        logging.getLogger("vowen").warning("Member notification delivery unavailable")


async def run() -> None:
    settings = Settings()
    engine = engine_for(settings.database_url)
    try:
        if not await check_schema(engine):
            raise RuntimeError("Run migrations first")
    finally:
        await engine.dispose()
    logging.basicConfig(level=logging.WARNING)
    # aiogram/aiohttp debug logging is deliberately not enabled.
    async with Bot(settings.bot_token()) as bot:
        actual = await bot.get_me()
        if actual.username != settings.telegram_bot_username:
            raise RuntimeError("Configured bot username does not match token")
        dispatcher = Dispatcher()
        dispatcher.include_router(build_router(settings))
        worker_engine = engine_for(settings.database_url)
        worker_sessions = sessions_for(worker_engine)

        async def worker() -> None:
            while True:
                await deliver_updates(
                    worker_sessions,
                    settings.data_keyring_file,
                    bot,
                    settings.public_base_url,
                )
                await asyncio.sleep(5)

        delivery_task = asyncio.create_task(worker())
        try:
            await dispatcher.start_polling(bot, allowed_updates=["message", "callback_query"])
        finally:
            delivery_task.cancel()
            await asyncio.gather(delivery_task, return_exceptions=True)
            await worker_engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
