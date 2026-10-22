"""Upgrade only pristine, canonical device stubs; preserve every editorial change."""

from datetime import UTC, datetime
from importlib.resources import files
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import Device, PracticeDevice
from vowen.modules.wiki.models import WikiPage, WikiSection
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.schemas import WikiDocument, WikiSource
from vowen.modules.wiki.sections import lock_wiki, validate_tree
from vowen.modules.wiki.seed import NAMESPACE, pristine_reference_page, reference_stub


class DeviceArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[a-z]+(?:-[a-z]+)*$")
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=600)
    body: str = Field(default="", max_length=100000)
    sources: list[WikiSource] = Field(default_factory=list, max_length=20)


class DeviceCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["ru"]
    version: Literal[1]
    articles: list[DeviceArticle]


class DeviceImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0


def load_device_articles() -> list[DeviceArticle]:
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "devices-v1")
    corpus = DeviceCorpus.model_validate_json(root.joinpath("manifest.json").read_text("utf-8"))
    if len({article.code for article in corpus.articles}) != len(corpus.articles):
        raise ValueError("Duplicate device article code")
    result = []
    for article in corpus.articles:
        body = root.joinpath("articles", article.code + ".md").read_text("utf-8")
        if not body.strip():
            raise ValueError("Empty device article")
        result.append(DeviceArticle.model_validate({**article.model_dump(), "body": body}))
    return result


async def seed_device_articles(db: AsyncSession, actor_id: UUID) -> DeviceImportResult:
    articles = load_device_articles()
    tree = await lock_wiki(db, actor_id)
    references: dict[str, list[Device]] = {}
    for reference in await db.scalars(select(Device)):
        code = reference.extra.get("code")
        if isinstance(code, str):
            references.setdefault(code, []).append(reference)
    if any(len(references.get(article.code, [])) != 1 for article in articles):
        raise AppError(422, "INVALID_EDITORIAL_REFERENCE")

    result = DeviceImportResult()
    root_uid = uuid5(NAMESPACE, "devices")
    structure_changed = False
    if not await db.get(WikiSection, root_uid):
        db.add(WikiSection(uid=root_uid, title="Девайсы", sort_order=2))
        await db.flush()
        structure_changed = True
    validate_tree({s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))})

    for article in articles:
        reference = references[article.code][0]
        canonical_uid = uuid5(NAMESPACE, "devices:" + str(reference.uid))
        stub = reference_stub(reference, root_uid)
        page = await db.scalar(
            select(WikiPage).where(WikiPage.device_uid == reference.uid).with_for_update()
        )
        is_new = page is None
        if page is not None and not await pristine_reference_page(
            db, page, reference, "devices", root_uid
        ):
            result.skipped += 1
            continue

        practices = list(await db.scalars(
            select(PracticeDevice.practice_uid)
            .where(PracticeDevice.device_uid == reference.uid)
            .order_by(PracticeDevice.practice_uid)
        ))
        document = WikiDocument.model_validate({
            **stub.model_dump(),
            "summary": article.summary,
            "body": article.body,
            "practice_uids": practices,
            "sources": [s.model_dump() for s in stub.sources + article.sources],
        })
        if page is None:
            page = WikiPage(uid=canonical_uid, kind="encyclopedia", device_uid=reference.uid)
            db.add(page)
            await db.flush()
        revision = await add_revision(db, actor_id, page, document)
        revision.published_at = datetime.now(UTC)
        page.published_revision_uid = revision.uid
        if is_new:
            result.created += 1
        else:
            page.version += 1
            result.updated += 1
    if result.created or result.updated or structure_changed:
        tree.version += 1
    await db.flush()
    return result
