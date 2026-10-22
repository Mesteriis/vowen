import asyncio

import pytest
from sqlalchemy import delete, select
from test_references import seeded

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.references.description_refresh import (
    description_updates,
    refresh_reference_descriptions,
)
from vowen.modules.references.fixtures import CATALOGUES
from vowen.modules.references.models import PracticeBodyPart


async def participants(app):
    async with app.state.sessions() as db:
        users = list(await db.scalars(select(User)))
        return next(u.id for u in users if u.is_admin), next(u.id for u in users if not u.is_admin)


async def snapshot(app):
    async with app.state.sessions() as db:
        return {(kind, row.uid): {c.name: getattr(row, c.name) for c in model.__table__.columns}
                for kind, model in CATALOGUES.items() for row in await db.scalars(select(model))}


async def test_refresh_changes_only_expected_descriptions_and_is_repeatable(api):
    _, app, _, _ = await seeded(api, "v15")
    actor, _ = await participants(app)
    before = await snapshot(app)
    updates = {(kind, baseline["uid"]): description
               for kind, baseline, description in description_updates()}
    async with app.state.sessions.begin() as db:
        result = await refresh_reference_descriptions(db, actor)
        assert (result.updated, result.skipped, result.missing) == (138, 0, 0)
    after = await snapshot(app)
    assert before.keys() == after.keys()
    for key, original in before.items():
        assert after[key] == {**original, "description": updates.get(key, original["description"])}
    async with app.state.sessions.begin() as db:
        repeat = await refresh_reference_descriptions(db, actor)
        assert (repeat.updated, repeat.skipped, repeat.missing) == (0, 138, 0)
    assert await snapshot(app) == after


async def test_description_refresh_preserves_all_manually_modified_record_fields(api):
    _, app, _, _ = await seeded(api, "v15")
    actor, _ = await participants(app)
    updates = description_updates()
    async with app.state.sessions.begin() as db:
        for (kind, baseline, _), (field, value) in zip(updates, [
            ("description", "Моё личное пояснение"), ("name", "Мой вариант названия"),
            ("thumbnail", None), ("url", "https://example.org/reference"),
            ("extra", {"code": "custom-code"}),
        ], strict=False):
            row = await db.get(CATALOGUES[kind], baseline["uid"])
            setattr(row, field, value)
    before = await snapshot(app)
    async with app.state.sessions.begin() as db:
        result = await refresh_reference_descriptions(db, actor)
        assert (result.updated, result.skipped) == (133, 5)
    after = await snapshot(app)
    for kind, baseline, _ in updates[:5]:
        assert after[(kind, baseline["uid"])] == before[(kind, baseline["uid"])]


async def test_description_refresh_checks_permissions_and_serializes_concurrent_runs(api):
    _, app, _, _ = await seeded(api, "v15")
    actor, member = await participants(app)
    before = await snapshot(app)
    with pytest.raises(AppError) as denied:
        async with app.state.sessions.begin() as db:
            await refresh_reference_descriptions(db, member)
    assert denied.value.status == 403
    assert await snapshot(app) == before

    async def run():
        async with app.state.sessions.begin() as db:
            return await refresh_reference_descriptions(db, actor)

    results = await asyncio.gather(run(), run())
    assert sorted(r.updated for r in results) == [0, 138]
    assert sorted(r.skipped for r in results) == [0, 138]


async def test_current_install_is_unchanged_and_missing_rows_are_not_created(api):
    _, app, _, _ = await seeded(api)
    actor, _ = await participants(app)
    before = await snapshot(app)
    async with app.state.sessions.begin() as db:
        result = await refresh_reference_descriptions(db, actor)
        assert (result.updated, result.skipped, result.missing) == (0, 138, 0)
    assert await snapshot(app) == before

    # A missing fixture is not authorization to restore a deliberately removed record.
    kind, baseline, _ = next(u for u in description_updates() if u[0] == "body-parts")
    async with app.state.sessions.begin() as db:
        row = await db.get(CATALOGUES[kind], baseline["uid"])
        # Remove reference join rows before this test-only deletion.
        await db.execute(delete(PracticeBodyPart).where(
            PracticeBodyPart.body_part_uid == row.uid,
        ))
        await db.delete(row)
    async with app.state.sessions.begin() as db:
        result = await refresh_reference_descriptions(db, actor)
        assert (result.updated, result.skipped, result.missing) == (0, 137, 1)
        assert await db.get(CATALOGUES[kind], baseline["uid"]) is None
