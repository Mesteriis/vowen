"""Versioned fixture data with stable UUIDs, preserved when reseeded."""

import json
from importlib.resources import files
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.modules.references.models import (
    Allergen,
    BiologicalSex,
    BodyPart,
    Device,
    Gender,
    HealthCondition,
    InteractionFormat,
    Material,
    ParticipantComposition,
    Practice,
    PracticeBodyPart,
    PracticeCategory,
    PracticeDevice,
    ReferenceEntry,
    RelationshipType,
    RoleScenario,
    Timezone,
    Venue,
)

ReferenceKind = Literal[
    "biological-sex",
    "genders",
    "practices",
    "practice-categories",
    "participant-compositions",
    "devices",
    "body-parts",
    "materials",
    "role-scenarios",
    "interaction-formats",
    "venues",
    "health-conditions",
    "allergens",
    "timezones",
    "relationship-types",
]
CATALOGUES: dict[ReferenceKind, type[ReferenceEntry]] = {
    "biological-sex": BiologicalSex,
    "genders": Gender,
    "practice-categories": PracticeCategory,
    "practices": Practice,
    "devices": Device,
    "body-parts": BodyPart,
    "materials": Material,
    "role-scenarios": RoleScenario,
    "interaction-formats": InteractionFormat,
    "venues": Venue,
    "health-conditions": HealthCondition,
    "allergens": Allergen,
    "participant-compositions": ParticipantComposition,
    "timezones": Timezone,
    "relationship-types": RelationshipType,
}


def fixture_rows(kind: ReferenceKind) -> list[dict[str, Any]]:
    source = files("vowen.modules.references").joinpath("fixtures/v15", kind + ".json")
    rows: list[dict[str, Any]] = json.loads(source.read_text(encoding="utf-8"))
    for row in rows:
        row["uid"] = UUID(row["uid"])
        if row.get("category_uid"):
            row["category_uid"] = UUID(row["category_uid"])
    return rows


async def seed_references(db: AsyncSession) -> None:
    for kind, model in CATALOGUES.items():
        # Never overwrite a persisted record or a user-added practice.
        await db.execute(insert(model).values(fixture_rows(kind)).on_conflict_do_nothing())

    await db.execute(
        insert(PracticeDevice).values(link_rows("practice-devices")).on_conflict_do_nothing()
    )
    await db.execute(
        insert(PracticeBodyPart).values(link_rows("practice-body-parts")).on_conflict_do_nothing()
    )


def link_rows(kind: Literal["practice-devices", "practice-body-parts"]) -> list[dict[str, UUID]]:
    source = files("vowen.modules.references").joinpath("fixtures/v15", kind + ".json")
    data: list[dict[str, str]] = json.loads(source.read_text(encoding="utf-8"))
    return [{key: UUID(value) for key, value in row.items()} for row in data]
