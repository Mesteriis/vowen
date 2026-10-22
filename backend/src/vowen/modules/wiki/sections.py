from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.identity.administration import administrator
from vowen.modules.identity.models import AdministrationState
from vowen.modules.wiki.models import WikiRevision, WikiSection, WikiTreeState
from vowen.modules.wiki.queries import wiki_tree
from vowen.modules.wiki.schemas import WikiSectionSave, WikiTreeView


async def lock_wiki(db: AsyncSession, actor_id: UUID) -> WikiTreeState:
    state = await db.get(AdministrationState, 1, with_for_update=True, populate_existing=True)
    if state is None:
        raise AppError(503, "UNAVAILABLE")
    await administrator(db, actor_id)
    tree = await db.get(WikiTreeState, 1, with_for_update=True, populate_existing=True)
    if tree is None:
        raise AppError(503, "UNAVAILABLE")
    return tree


def validate_tree(nodes: dict[UUID, UUID | None]) -> None:
    for node in nodes:
        visited: set[UUID] = set()
        current: UUID | None = node
        while current is not None:
            if current in visited or len(visited) >= 8:
                raise AppError(422, "INVALID_TREE")
            visited.add(current)
            current = nodes[current]


async def save_section(
    db: AsyncSession, actor_id: UUID, uid: UUID | None, command: WikiSectionSave
) -> WikiTreeView:
    tree = await lock_wiki(db, actor_id)
    if tree.version != command.expected_tree_version:
        raise AppError(409, "VERSION_CONFLICT")
    section = await db.get(WikiSection, uid, populate_existing=True) if uid else None
    if uid and section is None:
        raise AppError(404, "NOT_FOUND")
    if section and command.expected_version != section.version:
        raise AppError(409, "VERSION_CONFLICT")
    if command.parent_uid and not await db.get(WikiSection, command.parent_uid):
        raise AppError(422, "INVALID_SECTION")
    if section is None:
        section = WikiSection(title=command.title)
        db.add(section)
        await db.flush()
    nodes = {s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))}
    nodes[section.uid] = command.parent_uid
    validate_tree(nodes)
    section.title, section.description = command.title, command.description
    section.parent_uid, section.sort_order = command.parent_uid, command.sort_order
    if uid:
        section.version += 1
    tree.version += 1
    await db.flush()
    return await wiki_tree(db)


async def delete_section(
    db: AsyncSession, actor_id: UUID, uid: UUID, expected_version: int, expected_tree_version: int
) -> WikiTreeView:
    tree = await lock_wiki(db, actor_id)
    section = await db.get(WikiSection, uid, populate_existing=True)
    if section is None:
        raise AppError(404, "NOT_FOUND")
    if tree.version != expected_tree_version or section.version != expected_version:
        raise AppError(409, "VERSION_CONFLICT")
    children = await db.scalar(
        select(WikiSection.uid).where(WikiSection.parent_uid == uid).limit(1)
    )
    used = await db.scalar(select(WikiRevision.uid).where(WikiRevision.section_uid == uid).limit(1))
    if children or used:
        raise AppError(409, "SECTION_IN_USE")
    await db.delete(section)
    tree.version += 1
    await db.flush()
    return await wiki_tree(db)
