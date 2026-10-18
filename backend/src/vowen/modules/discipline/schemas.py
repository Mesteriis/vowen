from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal[
    "planned",
    "proposed",
    "accepted",
    "in_progress",
    "completed",
    "confirmed",
    "disputed",
    "declined",
    "cancelled",
]
Action = Literal["start", "complete", "confirm", "cancel"]


class DisciplineContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=10000)
    conditions: str = Field(min_length=1, max_length=10000)
    punishment_type: Literal["physical", "ban", "other"] = "other"
    device: str | None = Field(default=None, min_length=1, max_length=100)
    body_part: str | None = Field(default=None, min_length=1, max_length=100)
    strike_count: int | None = Field(default=None, ge=1, le=1000000, strict=True)
    intensity: int | None = Field(default=None, ge=1, le=10, strict=True)
    ban_days: int | None = Field(default=None, ge=1, le=36500, strict=True)
    assignment_title: str = Field(default="", max_length=200)
    assignment_comment: str = Field(default="", max_length=5000)
    deadline: datetime | None = None
    rule_version_id: UUID | None = None
    occurrence_id: UUID | None = None

    @model_validator(mode="after")
    def typed_parameters(self) -> "DisciplineContent":
        physical = (self.device, self.body_part, self.strike_count, self.intensity)
        if self.punishment_type == "physical":
            if any(value is None for value in physical) or self.ban_days is not None:
                raise ValueError("Physical parameters required; ban duration not applicable")
            assert self.device is not None and self.body_part is not None
            if not self.device.strip() or not self.body_part.strip():
                raise ValueError("Blank dictionary value")
        elif any(value is not None for value in physical):
            raise ValueError("Physical parameters only apply to physical punishment")
        if (self.punishment_type == "ban") != (self.ban_days is not None):
            raise ValueError("Ban duration required only for bans")
        return self

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


class DisciplineDictionaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def trimmed(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Blank dictionary value")
        return value


class PunishmentTemplateContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    conditions: str = Field(default="", max_length=10000)
    punishment_type: Literal["physical", "ban", "other"]
    device: str | None = Field(default=None, min_length=1, max_length=100)
    body_part: str | None = Field(default=None, min_length=1, max_length=100)
    strike_count: int | None = Field(default=None, ge=1, le=1000000, strict=True)
    ban_days: int | None = Field(default=None, ge=1, le=36500, strict=True)

    @model_validator(mode="after")
    def parameters(self) -> "PunishmentTemplateContent":
        if not self.title.strip():
            raise ValueError("Blank title")
        DisciplineContent(
            description=self.description,
            conditions=self.conditions or self.description,
            punishment_type=self.punishment_type,
            device=self.device,
            body_part=self.body_part,
            strike_count=self.strike_count,
            ban_days=self.ban_days,
            intensity=1 if self.punishment_type == "physical" else None,
        )
        return self


class PunishmentTemplateCreate(PunishmentTemplateContent):
    relation_id: UUID


class PunishmentTemplateEdit(PunishmentTemplateContent):
    expected_version: int = Field(ge=1)


class PunishmentTemplateView(PunishmentTemplateContent):
    id: UUID
    relation_id: UUID
    revision: int
    can_edit: bool


class PunishmentAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    idempotency_key: UUID
    intensity: int | None = Field(default=None, ge=1, le=10, strict=True)
    comment: str = Field(default="", max_length=5000)
    rule_version_id: UUID | None = None
