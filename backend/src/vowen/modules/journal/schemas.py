from datetime import date as EntryDate
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InkPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    p: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)


class InkStroke(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color: Literal["ivory", "gold", "rose"] = "ivory"
    width: float = Field(default=0.003, ge=0.001, le=0.01, allow_inf_nan=False)
    points: list[InkPoint] = Field(min_length=1, max_length=1500)


class InkDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    strokes: list[InkStroke] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def bounded(self) -> "InkDocument":
        if sum(len(stroke.points) for stroke in self.strokes) > 5000:
            raise ValueError("Too many ink points")
        return self


class JournalContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: EntryDate
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=100000)
    handwriting: InkDocument | None = None
    mood: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=30)
    visibility: Literal["private", "selected", "all_current_members"] = "private"
    reader_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    published: bool = False

    @field_validator("title")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank content")
        return value

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not t.strip() or len(t) > 100 for t in value):
            raise ValueError("Invalid tags")
        return value

    @model_validator(mode="after")
    def audience_valid(self) -> "JournalContent":
        if not self.text.strip() and not (self.handwriting and self.handwriting.strokes):
            raise ValueError("Entry requires text or handwriting")
        if len(set(self.reader_ids)) != len(self.reader_ids):
            raise ValueError("Duplicate reader")
        if self.visibility == "private" and self.reader_ids:
            raise ValueError("Private entries cannot have readers")
        return self


class JournalEdit(JournalContent):
    expected_version: int = Field(ge=1)
    refresh_audience: bool = False


class JournalView(JournalContent):
    id: UUID
    author_id: UUID
    revision: int
    created_at: datetime
    updated_at: datetime
