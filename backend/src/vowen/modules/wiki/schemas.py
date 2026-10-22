import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from vowen.modules.auth.schemas import Input


class WikiSource(Input):
    name: str | None = Field(default=None, max_length=160)
    url: str = Field(max_length=2000)

    @field_validator("url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        url = urlsplit(value)
        _ = url.port
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or any(ord(c) <= 32 for c in value)
            or "\\" in value
        ):
            raise ValueError("Unsafe source URL")
        return value


class WikiDocument(Input):
    section_uid: UUID
    title: str = Field(max_length=160)
    summary: str = Field(default="", max_length=600)
    body: str = Field(default="", max_length=100000)
    thumbnail: str | None = Field(default=None, max_length=500)
    practice_uids: list[UUID] = Field(default_factory=list, max_length=50)
    pose_uids: list[UUID] = Field(default_factory=list, max_length=50)
    device_uids: list[UUID] = Field(default_factory=list, max_length=50)
    sources: list[WikiSource] = Field(default_factory=list, max_length=20)

    @field_validator("thumbnail")
    @classmethod
    def asset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        root = Path(os.environ.get(
            "VOWEN_STATIC_ROOT", str(Path(__file__).resolve().parents[5] / "static" / "web"),
        ))
        if (
            not re.fullmatch(r"/(?!/)[A-Za-z0-9_./-]+", value)
            or ".." in value.split("/")
            or Path(value).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".avif")
        ):
            raise ValueError("Invalid thumbnail")
        target = (root / value.lstrip("/")).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError("Missing thumbnail")
        return value


class WikiPageCreate(Input):
    kind: Literal["encyclopedia", "article"]
    practice_uid: UUID | None = None
    pose_uid: UUID | None = None
    device_uid: UUID | None = None
    document: WikiDocument

    @model_validator(mode="after")
    def main_reference(self) -> Self:
        count = sum(v is not None for v in (self.practice_uid, self.pose_uid, self.device_uid))
        if count != (1 if self.kind == "encyclopedia" else 0):
            raise ValueError("Invalid main reference")
        return self


class WikiPageSave(Input):
    expected_version: int = Field(ge=1)
    document: WikiDocument


class WikiPublish(Input):
    expected_version: int = Field(ge=1)
    revision_uid: UUID


class WikiArchive(Input):
    expected_version: int = Field(ge=1)
    archived: bool


class WikiSectionSave(Input):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=600)
    parent_uid: UUID | None = None
    sort_order: int = Field(default=0, ge=0, le=1000000)
    expected_version: int | None = Field(default=None, ge=1)
    expected_tree_version: int = Field(ge=1)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty title")
        return value.strip()


class WikiSectionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uid: UUID
    parent_uid: UUID | None
    title: str
    description: str
    sort_order: int
    version: int


class WikiPageSummary(BaseModel):
    uid: UUID
    kind: str
    title: str
    summary: str
    section_uid: UUID
    thumbnail: str | None
    published_at: datetime | None


class WikiReferenceLink(BaseModel):
    reference_uid: UUID
    page_uid: UUID


class WikiTreeView(BaseModel):
    version: int
    sections: list[WikiSectionView]
    pages: list[WikiPageSummary]


class WikiSearchView(BaseModel):
    items: list[WikiPageSummary]
    total: int
    offset: int
    limit: int


class WikiEditView(BaseModel):
    uid: UUID
    kind: str
    version: int
    practice_uid: UUID | None
    pose_uid: UUID | None
    device_uid: UUID | None
    draft_revision_uid: UUID | None
    published_revision_uid: UUID | None
    archived_at: datetime | None
    document: WikiDocument


class WikiPageView(BaseModel):
    uid: UUID
    kind: str
    practice_uid: UUID | None
    pose_uid: UUID | None
    device_uid: UUID | None
    revision_uid: UUID
    document: WikiDocument
    author_id: UUID
    created_at: datetime
    published_at: datetime | None
    related_pages: list[WikiPageSummary]


class WikiRevisionView(BaseModel):
    uid: UUID
    author_id: UUID
    created_at: datetime
    published_at: datetime | None
    document: WikiDocument


class WikiSeedResult(BaseModel):
    created: int
    skipped: int
