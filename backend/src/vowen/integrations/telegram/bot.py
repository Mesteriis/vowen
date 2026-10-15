"""Trusted Telegram adapter. Never exposes approval through the public API."""

import asyncio
import logging
from uuid import UUID

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.auth.android_challenge import decide_challenge, present_challenge


def build_router(settings: Settings) -> Router:
    engine = engine_for(settings.database_url)
    sessions = sessions_for(engine)
    router = Router()

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
        await dispatcher.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(run())
