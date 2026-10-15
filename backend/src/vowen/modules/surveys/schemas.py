from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from vowen.modules.rituals.schemas import Schedule


class SurveyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    form_version_id: UUID
    recipient_id: UUID
    reader_ids: list[UUID] = Field(max_length=100)
    schedule: Schedule | None = None
    ritual_assignment_id: UUID | None = None
    ttl_days: int = Field(default=7, ge=1, le=7)
    retention_days: int = Field(default=90, ge=1, le=365)
    deliver: bool = True
    idempotency_key: UUID

    @field_validator("reader_ids")
    @classmethod
    def unique(cls, v: list[UUID]) -> list[UUID]:
        if len(set(v)) != len(v):
            raise ValueError("Duplicate reader")
        return v

    @model_validator(mode="after")
    def mode(self) -> "SurveyCreate":
        if (self.schedule is None) == (self.ritual_assignment_id is None):
            raise ValueError("Select exactly one survey trigger")
        return self


class SurveyView(SurveyCreate):
    id: UUID
    author_id: UUID
    revision: int
    owner_paused: bool
    recipient_paused: bool
    title: str
    source_effective: bool


class WaveView(BaseModel):
    id: UUID
    due_at: datetime
    occurrence_id: UUID | None
    invitation_id: UUID | None
    status: str
    reason: str | None


class SendWave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    idempotency_key: UUID
