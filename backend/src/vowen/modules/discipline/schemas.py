from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal[
    "proposed",
    "accepted",
    "in_progress",
    "completed",
    "confirmed",
    "disputed",
    "declined",
    "cancelled",
]
Action = Literal["accept", "start", "complete", "confirm", "dispute", "decline", "cancel"]


class DisciplineContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=10000)
    conditions: str = Field(min_length=1, max_length=10000)
    deadline: datetime | None = None
    rule_version_id: UUID | None = None
    occurrence_id: UUID | None = None

    @field_validator("description", "conditions")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank content")
        return value

    @field_validator("deadline")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value


class DisciplineCreate(DisciplineContent):
    recipient_id: UUID
    reviewer_ids: list[UUID] = Field(min_length=1, max_length=100)
    idempotency_key: UUID

    @field_validator("reviewer_ids")
    @classmethod
    def unique(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate reviewer")
        return value


class DisciplineEdit(DisciplineContent):
    expected_version: int = Field(ge=1)


class DisciplineDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    version_id: UUID
    action: Action
    comment: str = Field(default="", max_length=5000)


class DisciplineVersionView(DisciplineContent):
    id: UUID
    created_at: datetime
    rule_title: str | None


class DisciplineHistory(BaseModel):
    revision: int
    version_id: UUID
    actor_id: UUID
    status: Status
    created_at: datetime
    comment: str


class DisciplineView(BaseModel):
    id: UUID
    author_id: UUID
    recipient_id: UUID
    reviewer_ids: list[UUID]
    version_id: UUID
    revision: int
    status: Status
    effective: bool
    versions: list[DisciplineVersionView]
    history: list[DisciplineHistory]
