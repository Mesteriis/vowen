"""Space administration is independent of self-description and relationship authority."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.auth.schemas import Input
from vowen.modules.identity.models import AdministrationState, AdministratorEvent, User


class AdministratorMember(BaseModel):
    id: UUID
    display_name: str
    is_admin: bool


class AdministrationView(BaseModel):
    revision: int
    members: list[AdministratorMember]


class AdministrationCommand(Input):
    expected_revision: int = Field(ge=1)


async def administrator(db: AsyncSession, actor_id: UUID) -> User:
    actor = await db.scalar(
        select(User).where(User.id == actor_id).execution_options(populate_existing=True)
    )
    if actor is None or not actor.is_active or not actor.is_admin:
        raise AppError(403, "ACCESS_DENIED")
    return actor


async def administration_view(db: AsyncSession, actor_id: UUID) -> AdministrationView:
    state = await db.get(AdministrationState, 1, with_for_update=True, populate_existing=True)
    await administrator(db, actor_id)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    rows = await db.scalars(select(User).where(User.is_active).order_by(User.display_name, User.id))
    return AdministrationView(
        revision=state.revision,
        members=[
            AdministratorMember(id=u.id, display_name=u.display_name, is_admin=u.is_admin)
            for u in rows
        ],
    )


async def change_administrator(
    db: AsyncSession,
    actor_id: UUID,
    target_id: UUID,
    action: Literal["grant", "transfer"],
    expected_revision: int,
    now: datetime,
) -> None:
    # All grants/transfers/provisioning share a DB row lock, not an in-process mutex.
    state = await db.get(AdministrationState, 1, with_for_update=True, populate_existing=True)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    actor = await administrator(db, actor_id)
    if state.revision != expected_revision:
        raise AppError(409, "VERSION_CONFLICT")
    target = await db.scalar(
        select(User)
        .where(User.id == target_id, User.is_active)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if target is None:
        raise AppError(404, "NOT_FOUND")
    if target.id == actor.id:
        raise AppError(422, "INVALID_TARGET")
    if action == "grant" and target.is_admin:
        return  # Already granted: no duplicate audit record or revision.
    target.is_admin = True
    if action == "transfer":
        actor.is_admin = False
    state.revision += 1
    db.add(
        AdministratorEvent(actor_id=actor.id, target_id=target.id, action=action, created_at=now)
    )
    await db.flush()
