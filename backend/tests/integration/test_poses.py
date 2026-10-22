from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from test_references import seeded

from vowen.modules.references.fixtures import seed_references


async def test_poses_are_authenticated_linked_and_preserve_local_edits(api):
    from vowen.modules.references.models import Pose, PoseCategory

    client, app, _, member = await seeded(api)
    for kind in ["poses", "pose-categories"]:
        assert (await client.get("/api/v1/references/" + kind)).status_code == 401
    response = await client.get("/api/v1/references/poses", headers=member)
    assert response.status_code == 200
    poses = response.json()
    categories = (await client.get("/api/v1/references/pose-categories", headers=member)).json()
    assert len(poses) == 106 and len(categories) == 14
    assert all(p["category_uid"] in {c["uid"] for c in categories} for p in poses)
    async with app.state.sessions.begin() as db:
        pose = await db.scalar(select(Pose).limit(1))
        pose.description = "Local description"
        uid, category_uid = pose.uid, pose.category_uid
    async with app.state.sessions.begin() as db:
        await seed_references(db)
        assert (await db.get(Pose, uid)).description == "Local description"
    async with app.state.sessions() as db:
        with pytest.raises(IntegrityError):
            await db.execute(delete(PoseCategory).where(PoseCategory.uid == category_uid))
            await db.commit()
        await db.rollback()
        db.add(Pose(name="Unknown category", category_uid=uuid4()))
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()
        db.add(Pose(name=pose.name.upper(), category_uid=category_uid))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_slave_pose_migration_preserves_edited_rows_on_rollback_and_reapply(api):
    import runpy
    from pathlib import Path

    from sqlalchemy import func

    from vowen.modules.references.models import Pose, PoseCategory

    _, app, _, _ = await seeded(api)
    apply = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "migrations/versions/0047_slave_poses.py")
    )["apply"]
    async with app.state.engine.begin() as connection:
        category_uid = await connection.scalar(
            select(PoseCategory.uid).where(PoseCategory.name == "Позы рабыни")
        )
        edited_uid = await connection.scalar(
            select(Pose.uid).where(Pose.category_uid == category_uid).limit(1)
        )
        await connection.execute(
            Pose.__table__.update().where(Pose.uid == edited_uid).values(description="Local edit")
        )
        await connection.run_sync(lambda conn: apply(conn, reverse=True))
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 90
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == edited_uid))
            == "Local edit"
        )
        assert (
            await connection.scalar(
                select(PoseCategory.uid).where(PoseCategory.uid == category_uid)
            )
            == category_uid
        )
        await connection.run_sync(apply)
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 106
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == edited_uid))
            == "Local edit"
        )


async def test_modern_pose_migration_preserves_edits_and_custom_metadata(api):
    import runpy
    from pathlib import Path

    from sqlalchemy import func

    from vowen.modules.references.models import Pose

    client, app, _, member = await seeded(api)
    apply = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "migrations/versions/0048_modern_poses.py")
    )["apply"]
    async with app.state.engine.begin() as connection:
        new_uid = await connection.scalar(
            select(Pose.uid).where(Pose.extra["code"].astext == "modern-butterfly-edge")
        )
        existing_uid = await connection.scalar(
            select(Pose.uid).where(Pose.extra["code"].astext == "missionary")
        )
        custom = {"code": "missionary", "collections": ["personal"], "custom": True}
        await connection.execute(
            Pose.__table__.update().where(Pose.uid == new_uid).values(description="Local variant")
        )
        await connection.execute(
            Pose.__table__.update()
            .where(Pose.uid == existing_uid)
            .values(description="Local original", extra=custom)
        )
        await connection.run_sync(lambda conn: apply(conn, reverse=True))
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 64
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == new_uid))
            == "Local variant"
        )
        await connection.run_sync(apply)
        await connection.run_sync(apply)
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 106
        assert await connection.scalar(select(Pose.extra).where(Pose.uid == existing_uid)) == custom
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == existing_uid))
            == "Local original"
        )
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == new_uid))
            == "Local variant"
        )
    response = await client.get("/api/v1/references/poses", headers=member)
    assert response.status_code == 200
    assert len(response.json()) == 106
    assert (
        sum("modern-64" in row["extra"].get("collections", []) for row in response.json()) == 63
    )  # The custom collection remains untouched.


async def test_oral_pose_migration_preserves_edits_and_referenced_category(api):
    import runpy
    from pathlib import Path

    from sqlalchemy import func

    from vowen.modules.references.models import Pose, PoseCategory

    client, app, _, member = await seeded(api)
    apply = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "migrations/versions/0049_oral_poses.py")
    )["apply"]
    async with app.state.engine.begin() as connection:
        category_uid = await connection.scalar(
            select(PoseCategory.uid).where(PoseCategory.extra["code"].astext == "oral")
        )
        edited_uid = await connection.scalar(
            select(Pose.uid).where(Pose.category_uid == category_uid).limit(1)
        )
        await connection.execute(
            Pose.__table__.update().where(Pose.uid == edited_uid).values(description="Local oral")
        )
        await connection.run_sync(lambda conn: apply(conn, reverse=True))
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 99
        assert await connection.scalar(select(func.count()).select_from(PoseCategory)) == 13
        assert (
            await connection.scalar(
                select(PoseCategory.uid).where(PoseCategory.uid == category_uid)
            )
            == category_uid
        )
        await connection.run_sync(apply)
        await connection.run_sync(apply)
        assert await connection.scalar(select(func.count()).select_from(Pose)) == 106
        assert await connection.scalar(select(func.count()).select_from(PoseCategory)) == 14
        assert (
            await connection.scalar(select(Pose.description).where(Pose.uid == edited_uid))
            == "Local oral"
        )
    response = await client.get("/api/v1/references/poses", headers=member)
    assert response.status_code == 200
    assert sum(row["category_uid"] == str(category_uid) for row in response.json()) == 6
