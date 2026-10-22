from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import Device, Pose, Practice
from vowen.modules.wiki.models import (
    WikiPage,
    WikiRevision,
    WikiRevisionDevice,
    WikiRevisionPose,
    WikiRevisionPractice,
    WikiSection,
)
from vowen.modules.wiki.queries import revision_document
from vowen.modules.wiki.schemas import (
    WikiArchive,
    WikiDocument,
    WikiEditView,
    WikiPageCreate,
    WikiPageSave,
    WikiPublish,
    WikiRevisionView,
)
from vowen.modules.wiki.sections import lock_wiki


async def edit_view(db: AsyncSession, page: WikiPage) -> WikiEditView:
    revision = await db.get(WikiRevision, page.draft_revision_uid)
    if revision is None:
        raise AppError(404, "NOT_FOUND")
    return WikiEditView(
        uid=page.uid,
        kind=page.kind,
        version=page.version,
        practice_uid=page.practice_uid,
        pose_uid=page.pose_uid,
        device_uid=page.device_uid,
        draft_revision_uid=page.draft_revision_uid,
        published_revision_uid=page.published_revision_uid,
        archived_at=page.archived_at,
        document=await revision_document(db, revision),
    )


async def revision_view(db: AsyncSession, revision: WikiRevision) -> WikiRevisionView:
    return WikiRevisionView(
        uid=revision.uid,
        author_id=revision.author_id,
        created_at=revision.created_at,
        published_at=revision.published_at,
        document=await revision_document(db, revision),
    )


async def add_revision(
    db: AsyncSession, actor_id: UUID, page: WikiPage, document: WikiDocument
) -> WikiRevision:
    if not await db.get(WikiSection, document.section_uid):
        raise AppError(422, "INVALID_SECTION")
    for ref, values in [
        (Practice, document.practice_uids),
        (Pose, document.pose_uids),
        (Device, document.device_uids),
    ]:
        found = set(await db.scalars(select(ref.uid).where(ref.uid.in_(values))))
        if found != set(values):
            raise AppError(422, "INVALID_REFERENCE")
    revision = WikiRevision(
        page_uid=page.uid,
        author_id=actor_id,
        **document.model_dump(exclude={"practice_uids", "pose_uids", "device_uids"}),
    )
    db.add(revision)
    await db.flush()
    for model, field, values in [
        (WikiRevisionPractice, "practice_uid", document.practice_uids),
        (WikiRevisionPose, "pose_uid", document.pose_uids),
        (WikiRevisionDevice, "device_uid", document.device_uids),
    ]:
        for uid in set(values):
            db.add(model(revision_uid=revision.uid, **{field: uid}))
    page.draft_revision_uid = revision.uid
    await db.flush()
    return revision


async def create_page(db: AsyncSession, actor_id: UUID, command: WikiPageCreate) -> WikiEditView:
    await lock_wiki(db, actor_id)
    for model, uid, field in [
        (Practice, command.practice_uid, WikiPage.practice_uid),
        (Pose, command.pose_uid, WikiPage.pose_uid),
        (Device, command.device_uid, WikiPage.device_uid),
    ]:
        if uid:
            if not await db.get(model, uid):
                raise AppError(422, "INVALID_REFERENCE")
            if await db.scalar(select(WikiPage.uid).where(field == uid)):
                raise AppError(409, "PAGE_EXISTS")
    page = WikiPage(
        kind=command.kind,
        practice_uid=command.practice_uid,
        pose_uid=command.pose_uid,
        device_uid=command.device_uid,
    )
    db.add(page)
    await db.flush()
    await add_revision(db, actor_id, page, command.document)
    return await edit_view(db, page)


async def locked_page(db: AsyncSession, actor_id: UUID, uid: UUID, version: int) -> WikiPage:
    await lock_wiki(db, actor_id)
    page = await db.get(WikiPage, uid, with_for_update=True, populate_existing=True)
    if page is None:
        raise AppError(404, "NOT_FOUND")
    if page.version != version:
        raise AppError(409, "VERSION_CONFLICT")
    return page


async def save_page(
    db: AsyncSession, actor_id: UUID, uid: UUID, command: WikiPageSave
) -> WikiEditView:
    page = await locked_page(db, actor_id, uid, command.expected_version)
    await add_revision(db, actor_id, page, command.document)
    page.version += 1
    await db.flush()
    return await edit_view(db, page)


async def publish_page(
    db: AsyncSession, actor_id: UUID, uid: UUID, command: WikiPublish
) -> WikiEditView:
    page = await locked_page(db, actor_id, uid, command.expected_version)
    revision = await db.get(WikiRevision, command.revision_uid)
    if revision is None or revision.page_uid != uid:
        raise AppError(404, "NOT_FOUND")
    if page.archived_at or not revision.title.strip() or not revision.body.strip():
        raise AppError(422, "INVALID_PUBLICATION")
    page.published_revision_uid = revision.uid
    if revision.published_at is None:
        revision.published_at = datetime.now(UTC)
    page.version += 1
    await db.flush()
    return await edit_view(db, page)


async def set_archived(
    db: AsyncSession, actor_id: UUID, uid: UUID, command: WikiArchive
) -> WikiEditView:
    page = await locked_page(db, actor_id, uid, command.expected_version)
    page.archived_at = datetime.now(UTC) if command.archived else None
    page.version += 1
    await db.flush()
    return await edit_view(db, page)
