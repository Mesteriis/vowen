from datetime import timedelta

from conftest import NOW
from sqlalchemy import func, select
from test_android_login import challenge
from test_sessions import login, provision

from vowen.core.maintenance import prune_expired
from vowen.modules.auth.android_challenge import AndroidChallenge
from vowen.modules.auth.models import Session, TelegramAssertion


async def test_cleanup_preserves_live_session_and_expires_challenge(api):
    client, app = api
    await provision(app)
    await login(client)
    await challenge(client)
    async with app.state.sessions() as db:
        await prune_expired(db, NOW + timedelta(seconds=331))
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(AndroidChallenge)) == 0
        assert await db.scalar(select(func.count()).select_from(TelegramAssertion)) == 0
        assert await db.scalar(select(func.count()).select_from(Session)) == 1
        await prune_expired(db, NOW + timedelta(days=31))
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(Session)) == 0
