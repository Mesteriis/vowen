from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vowen.modules.rules.schemas import RuleContent

RequestKind = Literal["ritual_skip", "ritual_pause", "rule_add", "rule_edit", "rule_delete"]


class ChangeRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: RequestKind
    idempotency_key: UUID
    relation_id: UUID | None = None
    assignment_id: UUID | None = None
    occurrence_id: UUID | None = None
    expected_version: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1, max_length=10000)
    content: RuleContent | None = None

    @model_validator(mode="after")
    def target(self) -> "ChangeRequestCreate":
        if not self.reason.strip():
            raise ValueError("Blank reason")
        if self.kind == "rule_add":
            valid = (
                self.relation_id is not None
                and self.assignment_id is None
                and self.expected_version is None
            )
        else:
            valid = self.assignment_id is not None and self.expected_version is not None
        valid = valid and ((self.occurrence_id is not None) == (self.kind == "ritual_skip"))
        valid = valid and ((self.content is not None) == (self.kind in ("rule_add", "rule_edit")))
        if not valid:
            raise ValueError("Invalid proposal target or content")
        return self


class ChangeRequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    comment: str = Field(default="", max_length=10000)


class ChangeRequestView(BaseModel):
    title: str = ""
    id: UUID
    kind: RequestKind
    requester_id: UUID
    approver_id: UUID
    relation_id: UUID
    relation_version_id: UUID
    assignment_id: UUID | None
    occurrence_id: UUID | None
    rule_version_id: UUID | None
    result_assignment_id: UUID | None
    status: Literal["pending", "approved", "rejected", "withdrawn"]
    revision: int
    reason: str
    content: RuleContent | None
    comment: str
    created_at: datetime
    decided_at: datetime | None
    decision_actor_id: UUID | None
