from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RewardContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    conditions: str = Field(default="", max_length=10000)

    @field_validator("title", "description")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank content")
        return value


class RewardEdit(RewardContent):
    expected_version: int = Field(ge=1)


class RewardView(RewardContent):
    id: UUID
    version_id: UUID
    revision: int


class GrantCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reward_version_id: UUID
    recipient_id: UUID
    idempotency_key: UUID


class GrantTransitionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    action: Literal["accept", "decline", "deliver", "cancel"]


class GrantHistory(BaseModel):
    revision: int
    status: str
    actor_id: UUID
    created_at: datetime


class GrantView(RewardContent):
    id: UUID
    reward_version_id: UUID
    issuer_id: UUID
    recipient_id: UUID
    occurrence_id: UUID | None
    reward_policy_id: UUID | None
    revision: int
    status: str
    created_at: datetime
    history: list[GrantHistory]


class RewardNoticeView(BaseModel):
    id: UUID
    grant_id: UUID
    message: str = "У вас есть обновление в приложении"
    created_at: datetime
