from typing import cast
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import CheckConstraint, ForeignKey, Index, Table, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from vowen.core.database import Base


class ReferenceEntry(Base):
    __abstract__ = True
    uid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    icon: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    extra: Mapped[dict[str, JsonValue]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )


class BiologicalSex(ReferenceEntry):
    __tablename__ = "reference_biological_sex"


class Gender(ReferenceEntry):
    __tablename__ = "reference_genders"


class PracticeCategory(ReferenceEntry):
    __tablename__ = "reference_practice_categories"


class Practice(ReferenceEntry):
    __tablename__ = "reference_practices"
    category_uid: Mapped[UUID | None] = mapped_column(
        ForeignKey("reference_practice_categories.uid", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )


class ParticipantComposition(ReferenceEntry):
    __tablename__ = "reference_participant_compositions"


class Device(ReferenceEntry):
    __tablename__ = "reference_devices"


class BodyPart(ReferenceEntry):
    __tablename__ = "reference_body_parts"


class PracticeDevice(Base):
    __tablename__ = "reference_practice_devices"
    practice_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_practices.uid", ondelete="CASCADE"), primary_key=True
    )
    device_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_devices.uid", ondelete="RESTRICT"), primary_key=True, index=True
    )


class PracticeBodyPart(Base):
    __tablename__ = "reference_practice_body_parts"
    practice_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_practices.uid", ondelete="CASCADE"), primary_key=True
    )
    body_part_uid: Mapped[UUID] = mapped_column(
        ForeignKey("reference_body_parts.uid", ondelete="RESTRICT"), primary_key=True, index=True
    )


class Material(ReferenceEntry):
    __tablename__ = "reference_materials"


class RoleScenario(ReferenceEntry):
    __tablename__ = "reference_role_scenarios"


class InteractionFormat(ReferenceEntry):
    __tablename__ = "reference_interaction_formats"


class Venue(ReferenceEntry):
    __tablename__ = "reference_venues"


class HealthCondition(ReferenceEntry):
    __tablename__ = "reference_health_conditions"


class Allergen(ReferenceEntry):
    __tablename__ = "reference_allergens"


class Timezone(ReferenceEntry):
    __tablename__ = "reference_timezones"


class RelationshipType(ReferenceEntry):
    __tablename__ = "reference_relationship_types"


for model in (
    BiologicalSex,
    Gender,
    Practice,
    PracticeCategory,
    ParticipantComposition,
    Device,
    BodyPart,
    Material,
    RoleScenario,
    InteractionFormat,
    Venue,
    HealthCondition,
    Allergen,
    Timezone,
    RelationshipType,
):
    cast(Table, model.__table__).append_constraint(CheckConstraint("length(btrim(name)) > 0"))
    Index(model.__tablename__ + "_name_unique", func.lower(model.name), unique=True)
