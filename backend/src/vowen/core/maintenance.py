import asyncio
import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vowen.core.clock import Clock
from vowen.modules.auth.android_challenge import AndroidChallenge
from vowen.modules.auth.models import AccessToken, RefreshToken, Session, TelegramAssertion


async def prune_expired(db: AsyncSession, now: datetime) -> None:
    await db.execute(delete(AndroidChallenge).where(AndroidChallenge.expires_at <= now))
    await db.execute(delete(TelegramAssertion).where(TelegramAssertion.expires_at <= now))
    expired = select(Session.id).where(Session.expires_at <= now)
    await db.execute(delete(AccessToken).where(AccessToken.session_id.in_(expired)))
    await db.execute(delete(RefreshToken).where(RefreshToken.session_id.in_(expired)))
    await db.execute(delete(Session).where(Session.expires_at <= now))
    await db.execute(delete(AccessToken).where(AccessToken.expires_at <= now))


async def maintenance_loop(sessions: async_sessionmaker[AsyncSession], stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            async with sessions() as db, db.begin():
                await prune_expired(db, Clock().now())
        except Exception:
            # Do not log database exceptions that could contain sensitive bound parameters.
            logging.getLogger("vowen").warning("Expiry cleanup unavailable")
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except TimeoutError:
            pass
