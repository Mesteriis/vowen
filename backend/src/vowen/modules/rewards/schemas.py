from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

RewardCover = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:dinner|breakfast|cinema|walk|reward-(?:00[5-9]|0[1-9][0-9]|10[0-3]))$"
    ),
]
RewardCategory = Literal[
    "dates",
    "food",
    "drinks",
    "cinema",
    "music",
    "games",
    "outdoors",
    "travel",
    "creativity",
    "gifts",
    "care",
    "touch",
    "together",
]


class RewardContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    conditions: str = Field(default="", max_length=10000)
    cover: RewardCover = "dinner"
    category: RewardCategory = "together"

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
    action: Literal["accept", "decline", "deliver", "cancel", "approve", "reject", "redeem"]


class GrantHistory(BaseModel):
    revision: int
    status: str
    actor_id: UUID
    created_at: datetime


class GrantView(RewardContent):
    relation_id: UUID | None = None
    purchase_amount: int | None = None
    source: Literal["manual", "ritual", "purchase"] = "manual"
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


class ShopProductContent(RewardContent):
    price: int = Field(ge=1, le=1000000000, strict=True)
    audience_all: bool = True


class ShopProductEdit(ShopProductContent):
    expected_version: int = Field(ge=1)
