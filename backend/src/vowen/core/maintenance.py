import asyncio
import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vowen.core.clock import Clock
from vowen.modules.auth.android_challenge import AndroidChallenge
from vowen.modules.auth.models import AccessToken, RefreshToken, Session, TelegramAssertion
from vowen.modules.forms import service as forms
from vowen.modules.forms.models import GuestSession, Invitation, Receipt


async def prune_expired(db: AsyncSession, now: datetime) -> None:
    invitations = (
        await db.scalars(
            select(Invitation)
            .where(
                (Invitation.retention_until <= now)
                | (Invitation.expires_at <= now)
                | Invitation.revoked_at.is_not(None)
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    for invitation in invitations:
        response = await forms.submission(db, invitation)
        if invitation.retention_until <= now:
            await forms.withdraw(db, response, now)
        elif response.status == "draft":
            forms.clear(response)
    await db.execute(delete(GuestSession).where(GuestSession.expires_at <= now))
    await db.execute(
        delete(GuestSession).where(
            GuestSession.receipt_id.in_(select(Receipt.id).where(Receipt.expires_at <= now))
        )
    )
    await db.execute(delete(Receipt).where(Receipt.expires_at <= now))
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
