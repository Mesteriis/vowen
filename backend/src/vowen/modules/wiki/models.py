from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class WikiTreeState(Base):
    __tablename__ = "wiki_tree_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(default=1)


class WikiSection(Base):
    __tablename__ = "wiki_sections"
    __table_args__ = (CheckConstraint("parent_uid IS NULL OR parent_uid <> uid"),)
    uid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("wiki_sections.uid", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=1)


class WikiPage(Base):
    __tablename__ = "wiki_pages"
    __table_args__ = (
        CheckConstraint(
            "(kind='article' AND num_nonnulls(practice_uid,pose_uid,device_uid)=0) "
            "OR (kind='encyclopedia' AND "
            "num_nonnulls(practice_uid,pose_uid,device_uid)=1)",
            name="wiki_main_ref",
        ),
        ForeignKeyConstraint(
            ["uid", "draft_revision_uid"],
            ["wiki_revisions.page_uid", "wiki_revisions.uid"],
            name="wiki_draft_owner",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["uid", "published_revision_uid"],
            ["wiki_revisions.page_uid", "wiki_revisions.uid"],
            name="wiki_publication_owner",
            use_alter=True,
        ),
    )
    uid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(Text)
    practice_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("reference_practices.uid", ondelete="RESTRICT"), unique=True
    )
    pose_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("reference_poses.uid", ondelete="RESTRICT"), unique=True
    )
    device_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("reference_devices.uid", ondelete="RESTRICT"), unique=True
    )
    draft_revision_uid: Mapped[UUID | None] = mapped_column(nullable=True)
    published_revision_uid: Mapped[UUID | None] = mapped_column(nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(default=1)


class WikiRevision(Base):
    __tablename__ = "wiki_revisions"
    __table_args__ = (UniqueConstraint("page_uid", "uid", name="wiki_revision_owner"),)
    uid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    page_uid: Mapped[UUID] = mapped_column(ForeignKey("wiki_pages.uid"), index=True)
    section_uid: Mapped[UUID] = mapped_column(
        ForeignKey("wiki_sections.uid", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text)
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources: Mapped[list[dict[str, str | None]]] = mapped_column(JSONB, default=list)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WikiRevisionPractice(Base):
    __tablename__ = "wiki_revision_practices"
    revision_uid: Mapped[UUID] = mapped_column(ForeignKey("wiki_revisions.uid"), primary_key=True)
    practice_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_practices.uid", ondelete="RESTRICT"), primary_key=True
    )


class WikiRevisionPose(Base):
    __tablename__ = "wiki_revision_poses"
    revision_uid: Mapped[UUID] = mapped_column(ForeignKey("wiki_revisions.uid"), primary_key=True)
    pose_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_poses.uid", ondelete="RESTRICT"), primary_key=True
    )


class WikiRevisionDevice(Base):
    __tablename__ = "wiki_revision_devices"
    revision_uid: Mapped[UUID] = mapped_column(ForeignKey("wiki_revisions.uid"), primary_key=True)
    device_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_devices.uid", ondelete="RESTRICT"), primary_key=True
    )
