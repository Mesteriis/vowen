"""Explicit missing-only reference import. Never rewrite an editor's work."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid5

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.modules.references.models import (
    Device,
    Pose,
    PoseCategory,
    Practice,
    PracticeCategory,
    ReferenceEntry,
)
from vowen.modules.wiki.models import WikiPage, WikiRevision, WikiSection
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.queries import revision_document
from vowen.modules.wiki.schemas import WikiDocument, WikiSeedResult, WikiSource
from vowen.modules.wiki.sections import lock_wiki, validate_tree

NAMESPACE = UUID("a4542385-e05b-4ea1-864b-6ad90b4e8375")


def reference_stub(reference: ReferenceEntry, section_uid: UUID) -> WikiDocument:
    """Canonical original import document, also used to recognise untouched stubs."""
    sources = []
    if reference.url:
        try:
            sources.append(WikiSource(url=reference.url))
        except ValidationError:
            pass  # Invalid legacy reference URL is not copied into Wiki.
    image = None
    if reference.thumbnail:
        try:
            image = WikiDocument.asset(reference.thumbnail)
        except ValueError:
            pass
    body = "Краткая справочная карточка.\n\n" + reference.description
    origin = reference.extra.get("source_scope")
    if isinstance(origin, str):
        body += "\n\nРедакционное происхождение: " + origin
    return WikiDocument(
        section_uid=section_uid,
        title=reference.name[:160],
        summary=reference.description[:600],
        body=body[:100000],
        thumbnail=image,
        sources=sources,
    )


async def pristine_reference_page(
    db: AsyncSession,
    page: WikiPage,
    reference: ReferenceEntry,
    kind: Literal["devices", "practices", "poses"],
    section_uid: UUID,
) -> bool:
    """Recognise only the canonical first import; caller must hold lock_wiki."""
    if (
        page.uid != uuid5(NAMESPACE, kind + ":" + str(reference.uid))
        or page.version != 1
        or page.archived_at is not None
        or page.draft_revision_uid != page.published_revision_uid
        or page.published_revision_uid is None
    ):
        return False
    revision = await db.get(WikiRevision, page.published_revision_uid)
    count = await db.scalar(
        select(func.count()).select_from(WikiRevision).where(WikiRevision.page_uid == page.uid)
    )
    return (
        count == 1
        and revision is not None
        and (await revision_document(db, revision)) == reference_stub(reference, section_uid)
    )


async def seed_reference_pages(db: AsyncSession, actor_id: UUID) -> WikiSeedResult:
    tree = await lock_wiki(db, actor_id)
    created, skipped = 0, 0
    structure_changed = False
    for order, (kind, title, model, category_model, field) in enumerate(
        [
            ("practices", "Практики", Practice, PracticeCategory, "practice_uid"),
            ("poses", "Позы", Pose, PoseCategory, "pose_uid"),
            ("devices", "Девайсы", Device, None, "device_uid"),
            ("articles", "Статьи", None, None, ""),
        ]
    ):
        root_uid = uuid5(NAMESPACE, kind)
        if not await db.get(WikiSection, root_uid):
            structure_changed = True
            db.add(WikiSection(uid=root_uid, title=title, sort_order=order))
            await db.flush()
        if model is None:
            continue
        categories: dict[UUID | None, UUID] = {}
        if category_model:
            for category in await db.scalars(select(category_model).order_by(category_model.uid)):
                uid = uuid5(NAMESPACE, kind + ":category:" + str(category.uid))
                categories[category.uid] = uid
                if not await db.get(WikiSection, uid):
                    structure_changed = True
                    db.add(
                        WikiSection(
                            uid=uid,
                            parent_uid=root_uid,
                            title=category.name,
                            description=category.description[:600],
                        )
                    )
            await db.flush()
        existing = set(await db.scalars(select(getattr(WikiPage, field))))
        for reference in await db.scalars(select(model).order_by(model.uid)):
            if reference.uid in existing:
                skipped += 1
                continue
            uid = uuid5(NAMESPACE, kind + ":" + str(reference.uid))
            page = WikiPage(uid=uid, kind="encyclopedia", **{field: reference.uid})
            db.add(page)
            await db.flush()
            document = reference_stub(
                reference, categories.get(getattr(reference, "category_uid", None), root_uid)
            )
            revision = await add_revision(db, actor_id, page, document)
            revision.published_at = datetime.now(UTC)
            page.published_revision_uid = revision.uid
            created += 1
    validate_tree({s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))})
    if created or structure_changed:
        tree.version += 1
    await db.flush()
    return WikiSeedResult(created=created, skipped=skipped)
