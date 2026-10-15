from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class Relation(Base):
    __tablename__ = "authority_relations"
    __table_args__ = (
        CheckConstraint("dominant_user_id <> submissive_user_id", name="no_self_relation"),
        Index(
            "one_current_directed_pair",
            "dominant_user_id",
            "submissive_user_id",
            unique=True,
            postgresql_where=text("status <> 'revoked'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dominant_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    submissive_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    version: Mapped[int] = mapped_column(Integer, default=1)
    # FK added after version table to support the circular, explicitly typed relationship.
    relation_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("relation_versions.id", use_alter=True, name="current_relation_version")
    )


class RelationVersion(Base):
    __tablename__ = "relation_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    relation_id: Mapped[UUID] = mapped_column(ForeignKey("authority_relations.id"))
    scopes: Mapped[list[str]] = mapped_column(JSONB)
    key_id: Mapped[str] = mapped_column(String(100))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class Consent(Base):
    __tablename__ = "agreement_consents"
    relation_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("relation_versions.id"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
