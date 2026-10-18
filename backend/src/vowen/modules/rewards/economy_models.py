from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class Wallet(Base):
    __tablename__ = "relation_wallets"
    relation_id: Mapped[UUID] = mapped_column(
        ForeignKey("authority_relations.id"), primary_key=True
    )


class ShopListing(Base):
    __tablename__ = "shop_listings"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    relation_id: Mapped[UUID | None] = mapped_column(ForeignKey("authority_relations.id"))
    reward_version_id: Mapped[UUID] = mapped_column(ForeignKey("reward_definition_versions.id"))
    price: Mapped[int]
    audience_all: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=True)
    revision: Mapped[int] = mapped_column(default=1)


class CurrencyEntry(Base):
    __tablename__ = "currency_entries"
    __table_args__ = (
        UniqueConstraint("relation_id", "actor_id", "idempotency_key"),
        UniqueConstraint("relation_id", "occurrence_id", "policy_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    relation_id: Mapped[UUID] = mapped_column(ForeignKey("relation_wallets.relation_id"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[UUID | None]
    occurrence_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_occurrences.id"))
    policy_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_reward_policies.id"))
    grant_id: Mapped[UUID | None] = mapped_column(ForeignKey("reward_grants.id"))
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("shop_listings.id"))
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ShopRelationPreference(Base):
    __tablename__ = "shop_relation_preferences"
    relation_id: Mapped[UUID] = mapped_column(
        ForeignKey("authority_relations.id"), primary_key=True
    )
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("reward_definitions.id"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(default=True)
    revision: Mapped[int] = mapped_column(default=1)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (UniqueConstraint("relation_id", "buyer_id", "idempotency_key"),)
    grant_id: Mapped[UUID] = mapped_column(ForeignKey("reward_grants.id"), primary_key=True)
    relation_id: Mapped[UUID] = mapped_column(ForeignKey("authority_relations.id"))
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("shop_listings.id"))
    buyer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int]
    idempotency_key: Mapped[UUID]
