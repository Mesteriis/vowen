"""Explicit Russian pose articles, upgrading only pristine reference stubs."""

from datetime import UTC, datetime
from importlib.resources import files
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import Pose, PoseCategory, PoseDevice
from vowen.modules.wiki.models import WikiPage, WikiSection
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.schemas import WikiDocument, WikiSource
from vowen.modules.wiki.sections import lock_wiki, validate_tree
from vowen.modules.wiki.seed import NAMESPACE, pristine_reference_page, reference_stub


class PoseArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=600)
    body: str = Field(default="", max_length=100000)
    sources: list[WikiSource] = Field(default_factory=list, max_length=20)


class PoseCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["ru"]
    version: Literal[1]
    reference_fixture_version: Literal[20]
    articles: list[PoseArticle]


class PoseImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0


def load_pose_articles() -> list[PoseArticle]:
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "poses-v1")
    corpus = PoseCorpus.model_validate_json(root.joinpath("manifest.json").read_text("utf-8"))
    if len({a.code for a in corpus.articles}) != len(corpus.articles):
        raise ValueError("Duplicate pose article code")
    result = []
    for article in corpus.articles:
        body = root.joinpath("articles", article.code + ".md").read_text("utf-8")
        if not body.strip():
            raise ValueError("Empty pose article")
        result.append(PoseArticle.model_validate({**article.model_dump(), "body": body}))
    return result


async def seed_pose_articles(db: AsyncSession, actor_id: UUID) -> PoseImportResult:
    articles = load_pose_articles()
    tree = await lock_wiki(db, actor_id)
    references: dict[str, list[Pose]] = {}
    for reference in await db.scalars(select(Pose)):
        code = reference.extra.get("code")
        if isinstance(code, str):
            references.setdefault(code, []).append(reference)
    if any(len(references.get(a.code, [])) != 1 for a in articles):
        raise AppError(422, "INVALID_EDITORIAL_REFERENCE")

    result = PoseImportResult()
    root_uid = uuid5(NAMESPACE, "poses")
    structure_changed = False
    if not await db.get(WikiSection, root_uid):
        db.add(WikiSection(uid=root_uid, title="Позы", sort_order=1))
        await db.flush()
        structure_changed = True
    selected_categories = {
        references[a.code][0].category_uid for a in articles
        if references[a.code][0].category_uid is not None
    }
    category_sections = {}
    for uid in selected_categories:
        category = await db.get(PoseCategory, uid)
        if category is None:
            raise AppError(422, "INVALID_EDITORIAL_REFERENCE")
        section_uid = uuid5(NAMESPACE, "poses:category:" + str(uid))
        category_sections[uid] = section_uid
        if not await db.get(WikiSection, section_uid):
            db.add(WikiSection(
                uid=section_uid, parent_uid=root_uid, title=category.name,
                description=category.description[:600],
            ))
            structure_changed = True
    await db.flush()
    validate_tree({s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))})

    for article in articles:
        reference = references[article.code][0]
        section_uid = category_sections.get(reference.category_uid, root_uid)
        stub = reference_stub(reference, section_uid)
        page = await db.scalar(select(WikiPage).where(
            WikiPage.pose_uid == reference.uid,
        ).with_for_update())
        is_new = page is None
        if page is not None and not await pristine_reference_page(
            db, page, reference, "poses", section_uid
        ):
            result.skipped += 1
            continue
        devices = list(await db.scalars(
            select(PoseDevice.device_uid)
            .where(PoseDevice.pose_uid == reference.uid)
            .order_by(PoseDevice.device_uid)
        ))
        document = WikiDocument.model_validate({
            **stub.model_dump(),
            "summary": article.summary,
            "body": article.body,
            "device_uids": devices,
            "sources": [s.model_dump() for s in stub.sources + article.sources],
        })
        if page is None:
            page = WikiPage(
                uid=uuid5(NAMESPACE, "poses:" + str(reference.uid)),
                kind="encyclopedia", pose_uid=reference.uid,
            )
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
