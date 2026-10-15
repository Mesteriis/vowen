from datetime import date, datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Schedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["once", "daily", "weekly"]
    timezone: str = Field(max_length=100)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    start_date: date
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    window_hours: int = Field(default=24, ge=1, le=168)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Invalid timezone") from None
        return value

    @model_validator(mode="after")
    def days(self) -> "Schedule":
        if len(set(self.weekdays)) != len(self.weekdays) or any(
            d not in range(7) for d in self.weekdays
        ):
            raise ValueError("Invalid weekdays")
        if (self.kind == "weekly") != bool(self.weekdays):
            raise ValueError("Weekdays apply only to weekly schedules")
        return self


class RitualContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)

    @field_validator("title", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank content")
        return value


class RitualEdit(RitualContent):
    expected_version: int = Field(ge=1)


class RitualView(RitualContent):
    id: UUID
    version_id: UUID
    revision: int
    status: str


class EvidencePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    required: bool = False
    allowed_types: list[Literal["link", "photo", "video"]] = Field(
        default=["link", "photo", "video"], min_length=1, max_length=3
    )

    @field_validator("allowed_types")
    @classmethod
    def unique_types(
        cls, value: list[Literal["link", "photo", "video"]]
    ) -> list[Literal["link", "photo", "video"]]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate type")
        return value


class EvidenceView(BaseModel):
    id: UUID
    kind: str
    media_type: str
    size: int


class EvidenceUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    kind: Literal["photo", "video"]
    media_type: Literal["image/jpeg", "image/png", "video/mp4", "video/webm"]
    data_base64: str = Field(min_length=1, max_length=11184812)


class EvidenceDownload(EvidenceView):
    data_base64: str


class RitualAssign(BaseModel):
    reward_version_id: UUID | None = None
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    recipient_id: UUID
    reviewer_ids: list[UUID] = Field(max_length=100)
    approval_required: bool = True
    evidence_policy: EvidencePolicy = Field(default_factory=EvidencePolicy)
    schedule: Schedule

    @model_validator(mode="after")
    def reviewers(self) -> "RitualAssign":
        if len(set(self.reviewer_ids)) != len(self.reviewer_ids):
            raise ValueError("Duplicate reviewer")
        if self.approval_required and not self.reviewer_ids:
            raise ValueError("Reviewer required")
        if self.recipient_id in self.reviewer_ids:
            raise ValueError("Self review is forbidden")
        return self


class RitualAssignmentView(BaseModel):
    reward_policy_id: UUID | None = None
    evidence_policy: EvidencePolicy = Field(default_factory=EvidencePolicy)
    id: UUID
    ritual_version_id: UUID
    recipient_id: UUID
    issuer_id: UUID
    reviewer_ids: list[UUID]
    approval_required: bool
    revision: int
    status: str
    schedule: Schedule
    title: str
    description: str
    effective: bool


class ScheduleEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    schedule: Schedule


class ReportCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    idempotency_key: UUID
    text: str = Field(min_length=1, max_length=10000)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=3)
    links: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank report")
        return value


class ReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    decision: Literal["approved", "needs_changes"]
    comment: str = Field(default="", max_length=10000)


class RitualReportView(BaseModel):
    links: list[str] = Field(default_factory=list)
    attachments: list[EvidenceView] = Field(default_factory=list)
    attempt: int
    id: UUID
    text: str
    submitted_at: datetime
    decision: str | None
    reviewer_id: UUID | None
    reviewed_at: datetime | None
    comment: str | None


class OccurrenceView(BaseModel):
    evidence_policy: EvidencePolicy = Field(default_factory=EvidencePolicy)
    id: UUID
    assignment_id: UUID
    recipient_id: UUID
    title: str
    description: str
    local_day: date
    due_at: datetime
    expires_at: datetime
    revision: int
    status: str
    approval_required: bool
    can_report: bool
    can_review: bool
    reports: list[RitualReportView]


class RitualNoticeView(BaseModel):
    id: UUID
    occurrence_id: UUID | None
    assignment_id: UUID
    kind: str
    message: str = "У вас есть обновление в приложении"
    created_at: datetime
