from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation


async def direct_relationships(
    db: AsyncSession, owner_id: UUID, lock: bool = False
) -> dict[UUID, set[UUID]]:
    query = (
        select(Relation)
        .where(
            Relation.status == "active",
            or_(Relation.dominant_user_id == owner_id, Relation.submissive_user_id == owner_id),
        )
        .order_by(Relation.id)
    )
    if lock:
        query = query.with_for_update()
    owner = await db.get(User, owner_id)
    if owner is None or not owner.is_active or owner.paused:
        return {}
    result: dict[UUID, set[UUID]] = {}
    for relation in await db.scalars(query):
        other = (
            relation.submissive_user_id
            if relation.dominant_user_id == owner_id
            else relation.dominant_user_id
        )
        if (
            await db.scalar(
                select(User.id).where(and_(User.id == other, User.is_active, ~User.paused))
            )
            is not None
        ):
            result.setdefault(other, set()).add(relation.id)
    return result


async def direct_partners(db: AsyncSession, owner_id: UUID, lock: bool = False) -> set[UUID]:
    return set(await direct_relationships(db, owner_id, lock))
