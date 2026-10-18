from uuid import UUID

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class Profile(Base):
    __tablename__ = "participant_profiles"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(default=0)
    # Only scalar section fields; reference selections live in the typed FK tables below.
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    step: Mapped[int] = mapped_column(default=1)
    deferred: Mapped[bool] = mapped_column(default=False)
    completed: Mapped[bool] = mapped_column(default=False)
    draft_sequence: Mapped[int] = mapped_column(default=0)


class ProfileDraft(Base):
    __tablename__ = "participant_profile_drafts"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("participant_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    document: Mapped[dict] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer)
    visibility_edited: Mapped[bool] = mapped_column(default=False)
    base_profile_version: Mapped[int] = mapped_column(Integer)
    base_account_version: Mapped[int] = mapped_column(Integer)
    step: Mapped[int] = mapped_column(default=1)
    deferred: Mapped[bool] = mapped_column(default=False)


class ProfileSectionReader(Base):
    __tablename__ = "participant_profile_readers"
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("participant_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    relation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("authority_relations.id", ondelete="CASCADE"), nullable=True
    )
    section: Mapped[str] = mapped_column(String(20), primary_key=True)
    reader_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class PracticePreference(Base):
    __tablename__ = "participant_practice_preferences"
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("participant_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    practice_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_practices.uid", ondelete="RESTRICT"), primary_key=True
    )
    attitude: Mapped[str] = mapped_column(String(20), default="not_specified")
    experience: Mapped[str] = mapped_column(String(20), default="not_specified")
    participation: Mapped[str] = mapped_column(String(20), default="not_specified")
    conditions: Mapped[str] = mapped_column(String(2000), default="")


# Each selection has a distinct FK target. No polymorphic reference keys.
LINK_TARGETS = {
    "sex_preference": "reference_biological_sex",
    "gender_preference": "reference_genders",
    "relationship_type_uids": "reference_relationship_types",
    "composition_uids": "reference_participant_compositions",
    "interaction_format_uids": "reference_interaction_formats",
    "devices": "reference_devices",
    "body_parts": "reference_body_parts",
    "materials": "reference_materials",
    "role_scenarios": "reference_role_scenarios",
    "venues": "reference_venues",
    "condition_uids": "reference_health_conditions",
    "allergen_uids": "reference_allergens",
    "care_practice_uids": "reference_practices",
    "biological_sex_uid": "reference_biological_sex",
    "gender_uid": "reference_genders",
}
LINK_TABLES = {
    key: Table(
        "participant_profile_" + key,
        Base.metadata,
        Column(
            "owner_id",
            ForeignKey("participant_profiles.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        Column("uid", ForeignKey(target + ".uid", ondelete="RESTRICT"), primary_key=True),
        Column("attributes", JSONB, nullable=False),
    )
    for key, target in LINK_TARGETS.items()
}
