from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.identity.models import AdministrationState, User, UserPreferences
from vowen.modules.identity.shop_roles import ShopRole


class ProvisionUserCommand(BaseModel):
    telegram_id: int = Field(gt=0, le=2**63 - 1, strict=True)
    display_name: str = Field(min_length=1, max_length=100)
    shop_role: ShopRole = "viewer"


async def create_user(db: AsyncSession, command: ProvisionUserCommand, now: datetime) -> User:
    state = await db.get(AdministrationState, 1, with_for_update=True)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    first = await db.scalar(select(User.id).limit(1)) is None
    user = User(**command.model_dump(), created_at=now, is_admin=first)
    try:
        async with db.begin_nested():
            db.add(user)
            state.revision += 1
            await db.flush()
            db.add(UserPreferences(user_id=user.id))
            await db.flush()
    except IntegrityError:
        raise AppError(409, "USER_EXISTS") from None
    return user


async def set_user_active(db: AsyncSession, telegram_id: int, active: bool, now: datetime) -> User:
    state = await db.get(AdministrationState, 1, with_for_update=True)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    if user is None:
        raise AppError(404, "NOT_FOUND")
    if user.is_active != active:
        state.revision += 1
        from vowen.modules.rituals.service import suspend

        await suspend(db, now, actor_id=user.id)
    user.is_active = active
    if not active:
        from vowen.modules.auth.service import revoke_user_sessions

        await revoke_user_sessions(db, user.id)
    return user
