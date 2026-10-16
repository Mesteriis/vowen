from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    relation_id: UUID
    reward_version_id: UUID
    price: int
    active: bool
    revision: int
    title: str
    description: str
    conditions: str


class PurchaseCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    idempotency_key: UUID
