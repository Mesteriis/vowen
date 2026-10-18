from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from vowen.modules.rewards.schemas import RewardCategory, RewardCover


class CreditCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: int = Field(ge=1, le=1000000000, strict=True)
    comment: str = Field(min_length=1, max_length=2000)
    idempotency_key: UUID

    @field_validator("comment")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Blank comment")
        return value


class CurrencyEntryView(BaseModel):
    id: UUID
    amount: int
    kind: str
    comment: str
    actor_id: UUID
    occurrence_id: UUID | None
    grant_id: UUID | None
    created_at: datetime


class WalletView(BaseModel):
    relation_id: UUID
    balance: int = Field(ge=0, le=9007199254740991)
    reserved: int = Field(default=0, ge=0)
    total_balance: int = Field(default=0, ge=0)
    entries: list[CurrencyEntryView]


class ListingCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reward_version_id: UUID
    price: int = Field(ge=1, le=1000000000, strict=True)


class ListingEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    price: int = Field(ge=1, le=1000000000, strict=True)
    active: bool


class ListingView(BaseModel):
    id: UUID
    relation_id: UUID | None
    product_id: UUID | None = None
    product_revision: int = 1
    can_toggle: bool = False
    toggle_relation_id: UUID | None = None
    toggle_revision: int = 0
    relation_enabled: bool = True
    global_enabled: bool = True
    author_id: UUID | None = None
    can_manage: bool = False
    purchase_relation_id: UUID | None = None
    audience_all: bool = False
    reward_version_id: UUID
    price: int
    active: bool
    revision: int
    title: str
    description: str
    conditions: str
    cover: RewardCover = "dinner"
    category: RewardCategory = "together"


class PurchaseCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relation_id: UUID | None = None
    expected_version: int = Field(ge=1)
    idempotency_key: UUID


class ListingRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    expected_version: int = Field(ge=1)


class AvailabilityCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience_all: bool = False
    reward_version_id: UUID
    relation_ids: list[UUID] = Field(max_length=100)
    existing: list[ListingRevision] = Field(max_length=500)
    price: int = Field(ge=1, le=1000000000, strict=True)

    @field_validator("relation_ids")
    @classmethod
    def unique_relations(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate relation")
        return value

    @field_validator("existing")
    @classmethod
    def unique_listings(cls, value: list[ListingRevision]) -> list[ListingRevision]:
        if len({row.id for row in value}) != len(value):
            raise ValueError("Duplicate listing")
        return value


class ProductStateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    enabled: bool


class RelationProductCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    enabled: bool


class ProductRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
