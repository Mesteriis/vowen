from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleContent(BaseModel):
    discipline: str = Field(default="", max_length=10000)
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)

    @field_validator("title", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank content")
        return value


class RuleEdit(RuleContent):
    expected_version: int = Field(ge=1)


class RuleView(RuleContent):
    id: UUID
    author_id: UUID
    revision: int
    version_id: UUID
    status: Literal["draft", "published", "archived"]


class RuleAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_version_id: UUID
    recipient_id: UUID
    manager_ids: list[UUID] = Field(max_length=100)

    @field_validator("manager_ids")
    @classmethod
    def unique(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate manager")
        return value


class RuleDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    rule_version_id: UUID


class RuleAssignmentView(BaseModel):
    discipline: str = ""
    id: UUID
    rule_id: UUID
    rule_version_id: UUID
    recipient_id: UUID
    manager_ids: list[UUID]
    revision: int
    status: Literal["pending_acceptance", "active", "paused", "revoked"]
    accepted_at: datetime | None
    decided_at: datetime | None
    effective: bool
    title: str
    description: str
