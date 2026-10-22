"""Explicit, conservative description refresh from frozen v15 to v21 fixtures."""

import json
from importlib.resources import files
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.modules.identity.administration import administrator
from vowen.modules.references.fixtures import CATALOGUES, ReferenceKind, fixture_rows

DESCRIPTION_KINDS: tuple[ReferenceKind, ...] = (
    "practices", "devices", "body-parts", "practice-categories",
)


class DescriptionRefreshResult(BaseModel):
    updated: int = 0
    skipped: int = 0
    missing: int = 0


def description_updates() -> list[tuple[ReferenceKind, dict[str, Any], str]]:
    """Frozen old rows make the operation independent of future editorial revisions."""
    updates = []
    root = files("vowen.modules.references").joinpath("fixtures", "v15")
    for kind in DESCRIPTION_KINDS:
        originals = json.loads(root.joinpath(kind + ".json").read_text("utf-8"))
        current = {r["uid"]: r for r in fixture_rows(kind)}
        for original in originals:
            for field in ("uid", "category_uid"):
                if original.get(field):
                    original[field] = UUID(original[field])
            newer = current.get(original["uid"])
            if newer is None or {k: v for k, v in original.items() if k != "description"} != {
                k: v for k, v in newer.items() if k != "description"
            }:
                raise ValueError("Description refresh changed reference identity or metadata")
            if original["description"] != newer["description"]:
                updates.append((kind, original, newer["description"]))
    return updates


async def refresh_reference_descriptions(
    db: AsyncSession, actor_id: UUID,
) -> DescriptionRefreshResult:
    await administrator(db, actor_id)
    result = DescriptionRefreshResult()
    # Stable ordering serializes repeated/concurrent runs without a global content lock.
    ordered = sorted(description_updates(), key=lambda u: (u[0], u[1]["uid"]))
    for kind, baseline, description in ordered:
        model = CATALOGUES[kind]
        row = await db.scalar(
            select(model).where(model.uid == baseline["uid"]).with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            result.missing += 1
        elif any(getattr(row, key) != value for key, value in baseline.items()):
            # A changed label, image, URL, category, extra field or description is a manual edit.
            result.skipped += 1
        else:
            row.description = description
            result.updated += 1
    await db.flush()
    return result
