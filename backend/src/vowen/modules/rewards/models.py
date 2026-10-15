from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class RewardDefinition(Base):
    __tablename__ = "reward_definitions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int]
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reward_definition_versions.id", use_alter=True, name="current_reward_version")
    )


class RewardVersion(Base):
    __tablename__ = "reward_definition_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("reward_definitions.id"))
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class RewardPolicy(Base):
    __tablename__ = "ritual_reward_policies"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("ritual_assignments.id"))
    reward_version_id: Mapped[UUID] = mapped_column(ForeignKey("reward_definition_versions.id"))
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RewardGrant(Base):
    __tablename__ = "reward_grants"
    __table_args__ = (
        UniqueConstraint("issuer_id", "idempotency_key"),
        UniqueConstraint("occurrence_id", "reward_policy_id", "recipient_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reward_version_id: Mapped[UUID] = mapped_column(ForeignKey("reward_definition_versions.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    occurrence_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_occurrences.id"))
    reward_policy_id: Mapped[UUID | None] = mapped_column(ForeignKey("ritual_reward_policies.id"))
    idempotency_key: Mapped[UUID | None]
    revision: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RewardTransition(Base):
    __tablename__ = "reward_transitions"
    __table_args__ = (UniqueConstraint("grant_id", "revision"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    grant_id: Mapped[UUID] = mapped_column(ForeignKey("reward_grants.id"))
    revision: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RewardNotice(Base):
    __tablename__ = "reward_notices"
    __table_args__ = (UniqueConstraint("grant_id", "user_id", "revision"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    grant_id: Mapped[UUID] = mapped_column(ForeignKey("reward_grants.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
