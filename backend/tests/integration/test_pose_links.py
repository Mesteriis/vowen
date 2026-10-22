import runpy
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from test_references import seeded

from vowen.modules.references.fixtures import fixture_rows, link_rows, seed_references
from vowen.modules.references.models import (
    Device,
    ParticipantComposition,
    Pose,
    PoseCategory,
    PoseComposition,
    PoseDevice,
)


async def test_pose_links_are_authenticated_and_match_fixtures(api):
    client, app, _, member = await seeded(api)
    assert (await client.get("/api/v1/references/poses")).status_code == 401
    response = await client.get("/api/v1/references/poses", headers=member)
    assert response.status_code == 200
    for view in response.json():
        uid = UUID(view["uid"])
        for kind, field, public in (
            ("pose-devices", "device_uid", "device_uids"),
            ("pose-compositions", "composition_uid", "composition_uids"),
        ):
            expected = sorted(str(row[field]) for row in link_rows(kind) if row["pose_uid"] == uid)
            assert view[public] == expected
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        await seed_references(db)
        assert await db.scalar(select(func.count()).select_from(PoseDevice)) == 12
        assert await db.scalar(select(func.count()).select_from(PoseComposition)) == 9


async def test_pose_links_enforce_fk_unique_restrict_and_cascade(api):
    _, app, _, _ = await seeded(api)
    pose_uid, device_uid = uuid4(), uuid4()
    category_uid = fixture_rows("pose-categories")[0]["uid"]
    composition_uid = fixture_rows("participant-compositions")[0]["uid"]
    async with app.state.sessions.begin() as db:
        db.add(Device(uid=device_uid, name="Link test device"))
        db.add(Pose(uid=pose_uid, name="Link test pose", category_uid=category_uid))
        await db.flush()
        db.add(PoseDevice(pose_uid=pose_uid, device_uid=device_uid))
        db.add(PoseComposition(pose_uid=pose_uid, composition_uid=composition_uid))
    async with app.state.sessions() as db:
        for target, uid in ((Device, device_uid), (ParticipantComposition, composition_uid)):
            with pytest.raises(IntegrityError):
                await db.execute(delete(target).where(target.uid == uid))
                await db.commit()
            await db.rollback()
        for row in (
            PoseDevice(pose_uid=pose_uid, device_uid=device_uid),
            PoseComposition(pose_uid=pose_uid, composition_uid=composition_uid),
            PoseDevice(pose_uid=uuid4(), device_uid=device_uid),
            PoseComposition(pose_uid=pose_uid, composition_uid=uuid4()),
        ):
            db.add(row)
            with pytest.raises(IntegrityError):
                await db.commit()
            await db.rollback()
        await db.execute(delete(Pose).where(Pose.uid == pose_uid))
        await db.commit()
        assert await db.get(PoseDevice, (pose_uid, device_uid)) is None
        assert await db.get(PoseComposition, (pose_uid, composition_uid)) is None


async def test_pose_section_data_rollback_preserves_edited_pose_and_custom_links(api):
    _, app, _, _ = await seeded(api)
    apply = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "migrations/versions/0050_pose_sections.py")
    )["apply"]
    async with app.state.engine.begin() as connection:
        edited_uid = await connection.scalar(
            select(Pose.uid).where(Pose.extra["code"].astext == "equipment-bench-prone")
        )
        device_uid = fixture_rows("devices")[0]["uid"]
        await connection.execute(
            Pose.__table__.update().where(Pose.uid == edited_uid).values(description="Local bench")
        )
        await connection.execute(
            PoseDevice.__table__.insert().values(pose_uid=edited_uid, device_uid=device_uid)
        )
        await connection.run_sync(lambda conn: apply(conn, reverse=True))
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 93
        assert await connection.scalar(select(func.count()).select_from(PoseCategory)) == 12
        assert await connection.scalar(select(func.count()).select_from(PoseDevice)) == 1
        await connection.run_sync(apply)
        await connection.run_sync(apply)
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 106
        assert await connection.scalar(select(func.count()).select_from(PoseCategory)) == 14
        assert await connection.scalar(select(func.count()).select_from(PoseDevice)) == 13
        assert await connection.scalar(select(func.count()).select_from(PoseComposition)) == 9
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == edited_uid))
            == "Local bench"
        )
