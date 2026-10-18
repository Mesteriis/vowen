"""Explicit shop capability, separate from self-editable profile labels."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.identity.models import User


async def shop_user(
    db: AsyncSession, uid: UUID, *, manage: bool = False, write: bool = False, lock: bool = False
) -> User:
    user = await db.get(User, uid, with_for_update=lock, populate_existing=True)
    if user is None or not user.is_active:
        raise AppError(403, "ACCESS_DENIED")
    if manage and user.shop_role != "dominant":
        raise AppError(403, "ACCESS_DENIED")
    if write and user.paused:
        raise AppError(403, "ACCESS_DENIED")
    return user
