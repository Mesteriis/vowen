from uuid import UUID

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import EditMessageReplyMarkup, SendMessage
from aiogram.types import Chat, Message, Update
from aiogram.types import User as TelegramUser
from conftest import BOT_TOKEN, NOW
from test_android_login import challenge
from test_sessions import provision

from vowen.integrations.telegram.bot import build_router
from vowen.modules.auth.android_challenge import AndroidChallenge


class TelegramTransport(BaseSession):
    replies = []

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):
        if isinstance(method, (SendMessage, EditMessageReplyMarkup)):
            return Message(
                message_id=10,
                date=NOW,
                chat=Chat(id=100000000001, type="private"),
                text=getattr(method, "text", None),
            )
        if type(method).__name__ == "AnswerCallbackQuery":
            self.replies.append(method.text)
        return True

    async def stream_content(self, url, **kwargs):
        yield b""


async def test_bot_private_start_and_forwarded_callback_do_not_autoapprove(api, monkeypatch):
    client, app = api
    monkeypatch.setattr("vowen.integrations.telegram.bot.Clock.now", lambda self: NOW)
    await provision(app)
    await provision(app, 100000000002)
    created, nonce, start = await challenge(client)
    bot = Bot(BOT_TOKEN, session=TelegramTransport())
    dispatcher = Dispatcher()
    router = build_router(app.state.settings)
    dispatcher.include_router(router)
    actor = TelegramUser(id=100000000001, is_bot=False, first_name="Synthetic")
    message = Message(
        message_id=1,
        date=NOW,
        chat=Chat(id=actor.id, type="private"),
        from_user=actor,
        text="/start login_" + start,
        entities=[{"type": "bot_command", "offset": 0, "length": 6}],
    )
    await dispatcher.feed_update(bot, Update(update_id=1, message=message))
    async with app.state.sessions() as db:
        current = await db.get(AndroidChallenge, UUID(created["challenge_id"]))
        assert current.status == "pending"
        assert current.user_id is not None
    for update_id, sender, decision in [
        (2, 100000000002, "y"),
        (3, 100000000001, "y"),
        (4, 100000000001, "y"),
    ]:
        await dispatcher.feed_update(
            bot,
            Update.model_validate(
                {
                    "update_id": update_id,
                    "callback_query": {
                        "id": str(update_id),
                        "from": {"id": sender, "is_bot": False, "first_name": "Synthetic"},
                        "chat_instance": "synthetic",
                        "message": {
                            "message_id": 10,
                            "date": int(NOW.timestamp()),
                            "chat": {"id": 100000000001, "type": "private"},
                        },
                        "data": f"login:{decision}:{created['challenge_id']}",
                    },
                }
            ),
        )
        async with app.state.sessions() as db:
            current = await db.get(AndroidChallenge, UUID(created["challenge_id"]))
            assert current.status == ("pending" if update_id == 2 else "approved")
    for update_id in range(5, 36):
        await dispatcher.feed_update(
            bot,
            Update.model_validate(
                {
                    "update_id": update_id,
                    "callback_query": {
                        "id": str(update_id),
                        "from": {"id": 100000000001, "is_bot": False, "first_name": "Synthetic"},
                        "chat_instance": "synthetic",
                        "message": {
                            "message_id": 10,
                            "date": int(NOW.timestamp()),
                            "chat": {"id": 100000000001, "type": "private"},
                        },
                        "data": f"login:y:{created['challenge_id']}",
                    },
                }
            ),
        )
    assert bot.session.replies[-1] == "Too many attempts"
    await router.shutdown.trigger()
    await bot.session.close()


async def test_notification_contact_opt_in_does_not_create_member(api):
    from sqlalchemy import func, select

    from vowen.modules.forms.models import BotContact
    from vowen.modules.identity.models import User

    client, app = api
    bot = Bot(BOT_TOKEN, session=TelegramTransport())
    dispatcher = Dispatcher()
    router = build_router(app.state.settings)
    dispatcher.include_router(router)
    actor = TelegramUser(id=100000000009, is_bot=False, first_name="Synthetic")
    for index, command in enumerate(["/notifications_on", "/notifications_off"]):
        message = Message(
            message_id=index + 1,
            date=NOW,
            chat=Chat(id=actor.id, type="private"),
            from_user=actor,
            text=command,
            entities=[{"type": "bot_command", "offset": 0, "length": len(command)}],
        )
        await dispatcher.feed_update(bot, Update(update_id=index + 1, message=message))
        async with app.state.sessions() as db:
            contact = await db.get(BotContact, actor.id)
            assert contact is not None and contact.allowed == (index == 0)
            assert await db.scalar(select(func.count()).select_from(User)) == 0
    await router.emit_shutdown()
    await bot.session.close()
