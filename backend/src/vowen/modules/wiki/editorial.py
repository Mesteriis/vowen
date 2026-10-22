"""Explicit import of Russian editorial fixtures; existing pages are never overwritten."""

import json
from datetime import UTC, datetime
from importlib.resources import files
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.references.models import Device, Pose, Practice
from vowen.modules.wiki.models import WikiPage, WikiSection
from vowen.modules.wiki.pages import add_revision
from vowen.modules.wiki.schemas import WikiDocument, WikiSeedResult, WikiSource
from vowen.modules.wiki.sections import lock_wiki, validate_tree
from vowen.modules.wiki.seed import NAMESPACE


class EditorialArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z]+(?:-[a-z]+)*$")
    section: str
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=600)
    body: str = Field(default="", max_length=100000)
    practice_codes: list[str] = Field(default_factory=list, max_length=50)
    pose_codes: list[str] = Field(default_factory=list, max_length=50)
    device_codes: list[str] = Field(default_factory=list, max_length=50)
    sources: list[WikiSource] = Field(default_factory=list, max_length=20)


class EditorialCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str = Field(pattern="^ru$")
    version: int = Field(ge=1)
    sections: dict[str, str]
    articles: list[EditorialArticle]

    @model_validator(mode="after")
    def coherent(self) -> "EditorialCorpus":
        if len({article.key for article in self.articles}) != len(self.articles):
            raise ValueError("Duplicate editorial key")
        if any(article.section not in self.sections for article in self.articles):
            raise ValueError("Unknown editorial section")
        return self


def editorial_uid(key: str) -> UUID:
    # Edition upgrades keep the identity, edits and archive status of an article.
    return uuid5(NAMESPACE, "editorial:ru:" + key)


def load_editorial() -> EditorialCorpus:
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "v1")
    corpus = EditorialCorpus.model_validate(json.loads(root.joinpath("manifest.json").read_text()))
    for article in corpus.articles:
        body = root.joinpath("articles", article.key + ".md").read_text(encoding="utf-8")
        article.body = EditorialArticle.model_validate({
            **article.model_dump(), "body": body,
        }).body
        if not article.body.strip():
            raise ValueError("Empty editorial article")
    return corpus


async def seed_editorial_pages(db: AsyncSession, actor_id: UUID) -> WikiSeedResult:
    corpus = load_editorial()
    tree = await lock_wiki(db, actor_id)
    created, skipped = 0, 0
    structure_changed = False
    root_uid = uuid5(NAMESPACE, "articles")
    if not await db.get(WikiSection, root_uid):
        db.add(WikiSection(uid=root_uid, title="Статьи", sort_order=3))
        await db.flush()
        structure_changed = True
    for order, (key, title) in enumerate(corpus.sections.items()):
        uid = editorial_uid("section:" + key)
        if not await db.get(WikiSection, uid):
            db.add(WikiSection(uid=uid, parent_uid=root_uid, title=title, sort_order=order))
            structure_changed = True
    await db.flush()
    validate_tree({s.uid: s.parent_uid for s in await db.scalars(select(WikiSection))})

    reference_maps: dict[str, dict[str, list[UUID]]] = {}
    for kind, model in [("practice", Practice), ("pose", Pose), ("device", Device)]:
        codes: dict[str, list[UUID]] = {}
        for reference in await db.scalars(select(model)):
            code = reference.extra.get("code")
            if isinstance(code, str):
                codes.setdefault(code, []).append(reference.uid)
        reference_maps[kind] = codes

    for article in corpus.articles:
        uid = editorial_uid("article:" + article.key)
        if await db.get(WikiPage, uid):
            skipped += 1
            continue
        refs: dict[str, list[UUID]] = {}
        for kind in ("practice", "pose", "device"):
            ids = []
            for code in getattr(article, kind + "_codes"):
                matches = reference_maps[kind].get(code, [])
                if len(matches) != 1:
                    # Refuse ambiguous or absent references; the caller rolls back the import.
                    raise AppError(422, "INVALID_EDITORIAL_REFERENCE")
                ids.append(matches[0])
            refs[kind + "_uids"] = ids
        document = WikiDocument(
            section_uid=editorial_uid("section:" + article.section),
            title=article.title,
            summary=article.summary,
            body=article.body,
            sources=article.sources,
            practice_uids=refs["practice_uids"],
            pose_uids=refs["pose_uids"],
            device_uids=refs["device_uids"],
        )
        page = WikiPage(uid=uid, kind="article")
        db.add(page)
        await db.flush()
        revision = await add_revision(db, actor_id, page, document)
        revision.published_at = datetime.now(UTC)
        page.published_revision_uid = revision.uid
        created += 1
    if created or structure_changed:
        tree.version += 1
    await db.flush()
    return WikiSeedResult(created=created, skipped=skipped)
