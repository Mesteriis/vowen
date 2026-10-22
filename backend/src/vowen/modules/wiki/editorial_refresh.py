"""Explicit source-review upgrade; never replace a participant's edited publication."""

import hashlib
import json
from datetime import UTC, datetime
from importlib.resources import files
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import Device, Pose, Practice
from vowen.modules.wiki import editorial
from vowen.modules.wiki.editorial import EditorialArticle, editorial_uid
from vowen.modules.wiki.models import WikiPage, WikiRevision
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.queries import revision_document
from vowen.modules.wiki.schemas import WikiDocument
from vowen.modules.wiki.sections import lock_wiki


class EditorialBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    article: EditorialArticle
    body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EditorialRefreshResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0


def load_editorial_baselines() -> list[EditorialBaseline]:
    path = files("vowen.modules.wiki").joinpath("fixtures", "ru", "v1", "upgrade-baselines.json")
    payload = json.loads(path.read_text("utf-8"))
    if payload.get("version") != 1:
        raise ValueError("Unsupported editorial baseline")
    result = [EditorialBaseline.model_validate(a) for a in payload["articles"]]
    if len({b.article.key for b in result}) != len(result):
        raise ValueError("Duplicate editorial baseline")
    return result


def document_for(
    article: EditorialArticle, maps: dict[str, dict[str, list[UUID]]],
) -> WikiDocument:
    related: dict[str, list[UUID]] = {}
    for kind in ("practice", "pose", "device"):
        ids = []
        for code in getattr(article, kind + "_codes"):
            matches = maps[kind].get(code, [])
            if len(matches) != 1:
                raise AppError(422, "INVALID_EDITORIAL_REFERENCE")
            ids.append(matches[0])
        related[kind + "_uids"] = ids
    return WikiDocument(
        section_uid=editorial_uid("section:" + article.section),
        title=article.title, summary=article.summary, body=article.body,
        sources=article.sources,
        practice_uids=related["practice_uids"], pose_uids=related["pose_uids"],
        device_uids=related["device_uids"],
    )


async def refresh_editorial_pages(
    db: AsyncSession, actor_id: UUID,
) -> EditorialRefreshResult:
    # Both paths share the administrator/tree lock; missing-only import stays unchanged.
    tree = await lock_wiki(db, actor_id)
    baselines = {b.article.key: b for b in load_editorial_baselines()}
    corpus = editorial.load_editorial()
    if not set(baselines) <= {a.key for a in corpus.articles}:
        raise ValueError("Unknown baseline article")
    page_ids = [editorial_uid("article:" + a.key) for a in corpus.articles]
    existing = set(await db.scalars(select(WikiPage.uid).where(WikiPage.uid.in_(page_ids))))
    missing = await editorial.seed_editorial_pages(db, actor_id)
    result = EditorialRefreshResult(created=missing.created, skipped=missing.skipped)
    maps: dict[str, dict[str, list[UUID]]] = {}
    for kind, model in (("practice", Practice), ("pose", Pose), ("device", Device)):
        codes: dict[str, list[UUID]] = {}
        for reference in await db.scalars(select(model)):
            code = reference.extra.get("code")
            if isinstance(code, str):
                codes.setdefault(code, []).append(reference.uid)
        maps[kind] = codes

    for article in corpus.articles:
        baseline = baselines.get(article.key)
        if baseline is None or editorial_uid("article:" + article.key) not in existing:
            continue
        page = await db.scalar(select(WikiPage).where(
            WikiPage.uid == editorial_uid("article:" + article.key),
        ).with_for_update())
        if (
            page is None or page.kind != "article" or page.version != 1
            or page.archived_at is not None or page.published_revision_uid is None
            or page.draft_revision_uid != page.published_revision_uid
        ):
            continue
        revision = await db.get(WikiRevision, page.published_revision_uid)
        count = await db.scalar(select(func.count()).select_from(WikiRevision).where(
            WikiRevision.page_uid == page.uid,
        ))
        if revision is None or count != 1:
            continue
        if hashlib.sha256(revision.body.encode()).hexdigest() != baseline.body_sha256:
            continue
        previous = await revision_document(db, revision)
        expected = document_for(baseline.article.model_copy(update={"body": ""}), maps)
        # Junction tables represent sets: database retrieval order is not editorial content.
        related_fields = {"practice_uids", "pose_uids", "device_uids"}
        ignored = related_fields | {"body"}
        if previous.model_dump(exclude=ignored) != expected.model_dump(exclude=ignored):
            continue
        if any(set(getattr(previous, k)) != set(getattr(expected, k)) for k in related_fields):
            continue
        document = document_for(article, maps)
        if previous == document:
            continue
        updated = await add_revision(db, actor_id, page, document)
        updated.published_at = datetime.now(UTC)
        page.published_revision_uid = updated.uid
        page.version += 1
        result.updated += 1
        result.skipped -= 1
    if result.updated:
        tree.version += 1
    await db.flush()
    return result
