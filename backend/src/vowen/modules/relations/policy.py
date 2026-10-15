from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.auth.service import GuestPrincipal, MemberPrincipal, OperatorContext
from vowen.modules.identity.models import User
from vowen.modules.relations.models import Relation, RelationVersion


@dataclass(frozen=True)
class ResourceContext:
    """Server-loaded ACL only. Never construct this from a client-provided ACL."""

    target_user_id: UUID
    actor_ids: frozenset[UUID]


async def authorize(
    db: AsyncSession,
    principal: MemberPrincipal | GuestPrincipal | OperatorContext,
    action: str,
    context: ResourceContext,
) -> None:
    if not isinstance(principal, MemberPrincipal) or principal.user_id not in context.actor_ids:
        raise AppError(403, "ACCESS_DENIED")
    users = (
        await db.scalars(
            select(User).where(User.id.in_([principal.user_id, context.target_user_id]))
        )
    ).all()
    if not users or any(not u.is_active or u.paused for u in users):
        raise AppError(403, "ACCESS_DENIED")
    scopes = await db.scalar(
        select(RelationVersion.scopes)
        .join(Relation, Relation.relation_version_id == RelationVersion.id)
        .where(
            Relation.dominant_user_id == principal.user_id,
            Relation.submissive_user_id == context.target_user_id,
            Relation.status == "active",
        )
    )
    if scopes is None or action not in scopes:
        raise AppError(403, "ACCESS_DENIED")
