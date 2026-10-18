import asyncio
import json
from importlib.resources import files
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from test_sessions import auth, login, provision
from test_telegram_validation import signed

from vowen.modules.references.fixtures import CATALOGUES, fixture_rows, seed_references
from vowen.modules.references.models import Practice


async def seed_frozen_references(db, version):
    from sqlalchemy.dialects.postgresql import insert

    from vowen.modules.references.models import PracticeBodyPart, PracticeDevice

    for kind, model in [
        *CATALOGUES.items(),
        ("practice-devices", PracticeDevice),
        ("practice-body-parts", PracticeBodyPart),
    ]:
        rows = json.loads(
            files("vowen.modules.references")
            .joinpath("fixtures", version, kind + ".json")
            .read_text()
        )
        for row in rows:
            for key in row:
                if (key == "uid" or key.endswith("_uid")) and row[key] is not None:
                    row[key] = UUID(row[key])
        await db.execute(insert(model).values(rows).on_conflict_do_nothing())


async def seeded(api, reference_version=None):
    client, app = api
    await provision(app)
    await provision(app, 100000000002)
    async with app.state.sessions() as db, db.begin():
        if reference_version:
            await seed_frozen_references(db, reference_version)
        else:
            await seed_references(db)
    a = auth((await login(client)).json())
    b = auth((await login(client, signed(100000000002))).json())
    return client, app, a, b


async def test_fifteen_concrete_tables_and_authenticated_catalogues(api):
    client, app, _, member = await seeded(api)
    for kind, model in CATALOGUES.items():
        assert (await client.get("/api/v1/references/" + kind)).status_code == 401
        response = await client.get("/api/v1/references/" + kind, headers=member)
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == len(fixture_rows(kind))
        assert all(
            set(r)
            == {
                "uid",
                "name",
                "description",
                "icon",
                "thumbnail",
                "url",
                "extra",
                "category_uid",
                "device_uids",
                "body_part_uids",
            }
            for r in rows
        )
        assert len({r["uid"] for r in rows}) == len(rows)
        assert all(UUID(r["uid"]) and r["icon"] is None and r["url"] is None for r in rows)
        async with app.state.sessions() as db:
            columns = (
                await db.execute(
                    text(
                        "SELECT column_name,udt_name FROM information_schema.columns "
                        "WHERE table_name=:table_name"
                    ),
                    {"table_name": model.__tablename__},
                )
            ).all()
            assert dict(columns) == {
                "uid": "uuid",
                "name": "text",
                "description": "text",
                "icon": "text",
                "thumbnail": "text",
                "url": "text",
                "extra": "jsonb",
                **({"category_uid": "uuid"} if kind == "practices" else {}),
            }
    assert (await client.get("/api/v1/references/users", headers=member)).status_code == 422
    assert (
        await client.post("/api/v1/references/genders", headers=member, json={"name": "No"})
    ).status_code == 405
    assert len(fixture_rows("practices")) == 93
    zones = (await client.get("/api/v1/references/timezones", headers=member)).json()
    assert len(zones) == 24
    assert {"Europe/Madrid", "UTC"} <= {r["name"] for r in zones}
    for row in zones:
        assert ZoneInfo(row["extra"]["iana"])


async def test_only_admin_can_extend_practices_and_seed_is_non_destructive(api):
    client, app, admin, member = await seeded(api)
    payload = {
        "name": "Новая практика",
        "description": "Описание участника",
        "icon": "/icons/custom.webp",
        "thumbnail": "/references/custom.webp",
        "extra": {"nested": {"enabled": True}, "tags": ["custom"]},
    }
    assert (
        await client.post("/api/v1/administration/practices", headers=member, json=payload)
    ).status_code == 403
    response = await client.post("/api/v1/administration/practices", headers=admin, json=payload)
    assert response.status_code == 201
    created = response.json()
    assert UUID(created["uid"])
    assert created["url"] is None
    assert {
        k: v
        for k, v in created.items()
        if k not in {"uid", "url", "category_uid", "device_uids", "body_part_uids"}
    } == payload
    async with app.state.sessions() as db, db.begin():
        await seed_references(db)
        await seed_references(db)
    rows = (await client.get("/api/v1/references/practices", headers=member)).json()
    assert len(rows) == len(fixture_rows("practices")) + 1
    assert created in rows
    # User additions persist in fresh sessions after reseeding.
    async with app.state.sessions() as db:
        record = await db.get(Practice, UUID(created["uid"]))
        assert record.extra == payload["extra"]


async def test_concurrent_case_insensitive_duplicates_and_defaults(api):
    client, app, admin, _ = await seeded(api)
    responses = await asyncio.gather(
        *[
            client.post("/api/v1/administration/practices", headers=admin, json={"name": name})
            for name in ["Custom practice", " custom   PRACTICE "]
        ]
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    created = next(r.json() for r in responses if r.status_code == 201)
    assert created["description"] == "" and created["icon"] is None and created["extra"] == {}
    async with app.state.sessions() as db:
        assert (
            await db.scalar(select(func.count()).select_from(Practice))
            == len(fixture_rows("practices")) + 1
        )
    assert (
        await client.post(
            "/api/v1/administration/practices", headers=admin, json={"name": "массаж"}
        )
    ).status_code == 409
    for payload in [
        {"name": " "},
        {"name": "Invalid", "icon": "https://tracker.invalid/a"},
        {"name": "Invalid", "icon": "/../private"},
        {"name": "Invalid", "thumbnail": "https://tracker.invalid/a"},
        {"name": "Invalid", "thumbnail": "/../private"},
        {"name": "Invalid", "extra": []},
        {"name": "Invalid", "extra": {"x": "a" * 17000}},
        {"name": "Invalid", "uid": created["uid"]},
    ]:
        assert (
            await client.post("/api/v1/administration/practices", headers=admin, json=payload)
        ).status_code == 422


async def test_taxonomy_migration_preserves_custom_and_modified_records(api, monkeypatch):
    import runpy
    from pathlib import Path
    from uuid import uuid4

    from sqlalchemy import delete, select
    from sqlalchemy.dialects.postgresql import insert

    _, app, _, _ = await seeded(api)
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0030_practice_taxonomy.py")
    )
    old = migration["rows"]("0029-practices.json")
    new = migration["rows"]("0030-practices.json")
    modified = next(row for row in old if row["extra"]["code"] == "active-listening")
    custom_uid = uuid4()
    async with app.state.sessions() as db, db.begin():
        await db.execute(delete(Practice))
        await db.execute(insert(Practice).values(old))
        record = await db.get(Practice, modified["uid"])
        record.description = "User edited description"
        db.add(Practice(uid=custom_uid, name="Пользовательская практика"))
        await db.flush()

        def apply(session):
            with monkeypatch.context() as patch:
                patch.setattr(migration["op"], "get_bind", session.connection)
                migration["replace_unchanged"](old, new)
                migration["replace_unchanged"](old, new)

        await db.run_sync(apply)
    async with app.state.sessions() as db:
        entries = (await db.scalars(select(Practice))).all()
        assert len(entries) == 102
        assert await db.get(Practice, custom_uid)
        assert (await db.get(Practice, modified["uid"])).description == "User edited description"
        assert "Анальный секс" in {entry.name for entry in entries}
        assert "Совместная прогулка" not in {entry.name for entry in entries}


async def test_practice_category_creation_validation_and_foreign_key(api):
    from uuid import uuid4

    import pytest
    from sqlalchemy import delete
    from sqlalchemy.exc import IntegrityError

    from vowen.modules.references.models import PracticeCategory

    client, app, admin, member = await seeded(api)
    categories = (await client.get("/api/v1/references/practice-categories", headers=member)).json()
    assert len(categories) == 13
    assert "Контроль оргазма" in {row["name"] for row in categories}
    category_uid = categories[0]["uid"]
    practices = (await client.get("/api/v1/references/practices", headers=member)).json()
    assert all(row["category_uid"] in {c["uid"] for c in categories} for row in practices)
    assert all(
        "Категория:" not in row["description"] and "category" not in row["extra"]
        for row in practices
    )
    payload = {"name": "Практика с категорией", "category_uid": category_uid}
    assert (
        await client.post("/api/v1/administration/practices", headers=member, json=payload)
    ).status_code == 403
    response = await client.post("/api/v1/administration/practices", headers=admin, json=payload)
    assert response.status_code == 201
    assert response.json()["category_uid"] == category_uid
    invalid = await client.post(
        "/api/v1/administration/practices",
        headers=admin,
        json={"name": "Недопустимая категория", "category_uid": str(uuid4())},
    )
    assert invalid.status_code == 422
    async with app.state.sessions() as db, db.begin():
        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                db.add(Practice(name="Broken FK", category_uid=uuid4()))
                await db.flush()
        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                await db.execute(
                    delete(PracticeCategory).where(PracticeCategory.uid == UUID(category_uid))
                )
        await seed_references(db)
    rows = (await client.get("/api/v1/references/practices", headers=member)).json()
    assert response.json() in rows
    assert len(rows) == 94


async def test_refined_catalogue_migration_preserves_edits_and_used_categories(api):
    import runpy
    from pathlib import Path
    from uuid import uuid4

    from sqlalchemy import delete
    from sqlalchemy.dialects.postgresql import insert

    from vowen.modules.references.models import PracticeCategory

    _, app, _, _ = await seeded(api)
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0032_refine_practice_catalogue.py")
    )
    old_practices = migration["rows"]("0031", "practices")
    old_categories = migration["rows"]("0031", "practice-categories")
    mirrored = next(row for row in old_practices if row["extra"]["code"] == "mirror-masturbation")
    edited = next(row for row in old_practices if row["extra"]["code"] == "fellatio")
    bdsm = next(row["uid"] for row in old_categories if row["name"] == "BDSM")
    custom_uid = uuid4()
    async with app.state.sessions() as db, db.begin():
        await db.execute(delete(Practice))
        await db.execute(delete(PracticeCategory))
        await db.execute(insert(PracticeCategory).values(old_categories))
        await db.execute(insert(Practice).values(old_practices))
        (await db.get(Practice, mirrored["uid"])).description = "Keep edited variant"
        (await db.get(Practice, edited["uid"])).description = "Keep custom description"
        db.add(Practice(uid=custom_uid, name="Custom practice", category_uid=bdsm))
        await db.flush()

        def transition(session):
            connection = session.connection()
            migration["transition"](connection, "0031", "0032")
            migration["transition"](connection, "0031", "0032")
            migration["transition"](connection, "0032", "0031")
            migration["transition"](connection, "0031", "0032")

        await db.run_sync(transition)
    async with app.state.sessions() as db:
        entries = (await db.scalars(select(Practice))).all()
        assert len(entries) == 91  # 89 fixtures plus preserved edited variant and custom record.
        assert (await db.get(Practice, mirrored["uid"])).description == "Keep edited variant"
        assert (await db.get(Practice, edited["uid"])).description == "Keep custom description"
        assert (await db.get(Practice, custom_uid)).category_uid == bdsm
        assert await db.get(PracticeCategory, bdsm)
        assert "Боди-массаж" not in {row.name for row in entries}
        masturbation = next(row for row in entries if row.extra.get("code") == "masturbation")
        assert "Мастурбация перед зеркалом" in masturbation.extra["aliases"]
        assert masturbation.category_uid is not None


async def test_composition_and_group_seed_preserves_edits_and_stable_links(api):
    import runpy
    from pathlib import Path

    from vowen.modules.references.models import ParticipantComposition

    client, app, _, member = await seeded(api)
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0033_group_practices.py")
    )
    composition = next(
        row for row in fixture_rows("participant-compositions") if row["name"] == "МЖМ"
    )
    group = next(row for row in fixture_rows("practices") if row["name"] == "Секс втроём")
    async with app.state.sessions() as db, db.begin():
        (
            await db.get(ParticipantComposition, composition["uid"])
        ).description = "Custom composition text"
        (await db.get(Practice, group["uid"])).description = "Custom group text"
        await db.flush()
        await db.run_sync(lambda session: migration["seed"](session.connection()))
        await db.run_sync(lambda session: migration["seed"](session.connection()))
        await seed_references(db)
    entries = (
        await client.get("/api/v1/references/participant-compositions", headers=member)
    ).json()
    assert len(entries) == 10
    current = next(row for row in entries if row["name"] == "МЖМ")
    assert current["description"] == "Custom composition text"
    assert "ММЖ" in current["extra"]["aliases"]
    async with app.state.sessions() as db:
        record = await db.get(Practice, group["uid"])
        assert record.description == "Custom group text"
        assert record.category_uid == group["category_uid"]
        assert await db.scalar(select(func.count()).select_from(Practice)) == 93


async def test_equipment_many_to_many_create_validation_and_fk(api):
    from uuid import uuid4

    import pytest
    from sqlalchemy import delete
    from sqlalchemy.exc import IntegrityError

    from vowen.modules.references.models import Device, PracticeBodyPart, PracticeDevice

    client, app, admin, member = await seeded(api)
    device = fixture_rows("devices")[0]["uid"]
    part = fixture_rows("body-parts")[0]["uid"]
    payload = {
        "name": "Linked practice",
        "device_uids": [str(device), str(device)],
        "body_part_uids": [str(part)],
    }
    assert (
        await client.post("/api/v1/administration/practices", headers=member, json=payload)
    ).status_code == 403
    response = await client.post("/api/v1/administration/practices", headers=admin, json=payload)
    assert response.status_code == 201
    assert response.json()["device_uids"] == [str(device)]
    assert response.json()["body_part_uids"] == [str(part)]
    invalid = await client.post(
        "/api/v1/administration/practices",
        headers=admin,
        json={"name": "Invalid link", "device_uids": [str(uuid4())]},
    )
    assert invalid.status_code == 422
    async with app.state.sessions() as db, db.begin():
        assert await db.scalar(select(Practice.uid).where(Practice.name == "Invalid link")) is None
        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                await db.execute(delete(Device).where(Device.uid == device))
        await seed_references(db)
        uid = UUID(response.json()["uid"])
        assert (
            await db.scalar(
                select(func.count())
                .select_from(PracticeDevice)
                .where(PracticeDevice.practice_uid == uid)
            )
            == 1
        )
        assert (
            await db.scalar(
                select(func.count())
                .select_from(PracticeBodyPart)
                .where(PracticeBodyPart.practice_uid == uid)
            )
            == 1
        )
    rows = (await client.get("/api/v1/references/practices", headers=member)).json()
    assert response.json() in rows


async def test_additional_catalogues_reseed_preserves_custom_content(api):
    from uuid import uuid4

    from vowen.modules.references.models import (
        Allergen,
        HealthCondition,
        InteractionFormat,
        Material,
        RoleScenario,
        Venue,
    )

    client, app, _, member = await seeded(api)
    for kind, model in (
        ("materials", Material),
        ("role-scenarios", RoleScenario),
        ("interaction-formats", InteractionFormat),
        ("venues", Venue),
        ("health-conditions", HealthCondition),
        ("allergens", Allergen),
    ):
        uid = fixture_rows(kind)[0]["uid"]
        custom_uid = uuid4()
        async with app.state.sessions() as db, db.begin():
            (await db.get(model, uid)).description = "Preserved custom description"
            db.add(model(uid=custom_uid, name="Custom reference", description="Custom row"))
            await db.flush()
            await seed_references(db)
            await seed_references(db)
        rows = (await client.get("/api/v1/references/" + kind, headers=member)).json()
        assert len(rows) == len(fixture_rows(kind)) + 1
        assert (
            next(row for row in rows if row["uid"] == str(uid))["description"]
            == "Preserved custom description"
        )
        assert (
            next(row for row in rows if row["uid"] == str(custom_uid))["description"]
            == "Custom row"
        )
        assert (
            await client.post(
                "/api/v1/references/" + kind, headers=member, json={"name": "Forbidden"}
            )
        ).status_code == 405


async def test_structure_migration_preserves_edits_ids_and_equipment_links(api):
    import runpy
    from pathlib import Path

    from vowen.modules.references.models import Device, PracticeCategory, PracticeDevice

    _, app, _, _ = await seeded(api)
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0038_structure_existing.py")
    )
    device = next(row for row in fixture_rows("devices") if row["extra"]["code"] == "cuffs")
    rope = next(row for row in fixture_rows("devices") if row["extra"]["code"] == "rope")
    massage = next(row for row in fixture_rows("practices") if row["extra"]["code"] == "massage")
    care = next(
        row for row in fixture_rows("practice-categories") if row["extra"]["code"] == "care"
    )
    async with app.state.sessions() as db, db.begin():
        await db.run_sync(lambda session: migration["apply"](session.connection(), reverse=True))
        (await db.get(Device, device["uid"])).description = "Preserved device edit"
        (await db.get(Practice, massage["uid"])).description = "Preserved practice edit"
        await db.flush()
        await db.run_sync(lambda session: migration["apply"](session.connection()))
        await db.run_sync(lambda session: migration["apply"](session.connection()))
    async with app.state.sessions() as db:
        assert (await db.get(Device, device["uid"])).description == "Preserved device edit"
        assert (await db.get(Practice, massage["uid"])).description == "Preserved practice edit"
        assert (await db.get(Device, rope["uid"])).extra["group"] == "Средства фиксации"
        assert (await db.get(PracticeCategory, care["uid"])).name == "Восстановление и забота"
        assert await db.scalar(select(func.count()).select_from(Device)) == 62
        assert await db.scalar(select(func.count()).select_from(Practice)) == 93
        assert await db.scalar(select(func.count()).select_from(PracticeCategory)) == 13
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 21


async def test_thumbnail_migration_preserves_custom_assets_icons_and_other_fields(api):
    import runpy
    from pathlib import Path

    from sqlalchemy import update

    from vowen.modules.references.models import Device, PracticeDevice

    _, app, _, _ = await seeded(api)
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0040_reference_thumbnails.py")
    )
    rows = fixture_rows("devices")
    rope = next(row for row in rows if row["extra"]["code"] == "rope")
    cuffs = next(row for row in rows if row["extra"]["code"] == "cuffs")
    async with app.state.sessions() as db, db.begin():
        for model in CATALOGUES.values():
            await db.execute(update(model).values(thumbnail=None))
        record = await db.get(Device, rope["uid"])
        record.thumbnail = "/custom/rope.png"
        record.icon = "/custom/rope-icon.svg"
        record.description = "Custom description survives asset population"
        await db.flush()
        await db.run_sync(lambda session: migration["apply"](session.connection()))
        await db.run_sync(lambda session: migration["apply"](session.connection()))
    async with app.state.sessions() as db:
        record = await db.get(Device, rope["uid"])
        assert record.thumbnail == "/custom/rope.png"
        assert record.icon == "/custom/rope-icon.svg"
        assert record.description == "Custom description survives asset population"
        assert (await db.get(Device, cuffs["uid"])).thumbnail == cuffs["thumbnail"]
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 21
    async with app.state.sessions() as db, db.begin():
        await db.run_sync(lambda session: migration["apply"](session.connection(), reverse=True))
    async with app.state.sessions() as db:
        assert (await db.get(Device, rope["uid"])).thumbnail == "/custom/rope.png"
        assert (await db.get(Device, cuffs["uid"])).thumbnail is None


async def test_device_expansion_migration_preserves_edits_and_equipment_links(api):
    import json
    import runpy
    from pathlib import Path

    from vowen.modules.references.models import Device, PracticeDevice

    _, app, _, _ = await seeded(api, reference_version="v13")
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0041_extra_devices.py")
    )
    v13 = json.loads(
        (
            Path(__file__).parents[2] / "src/vowen/modules/references/fixtures/v13/devices.json"
        ).read_text()
    )
    for row in v13:
        row["uid"] = UUID(row["uid"])
    devices = {row["extra"]["code"]: row for row in v13}
    custom = devices["linear-sex-machine"]
    linked = devices["spreader-bar"]
    removable = devices["rotary-sex-machine"]
    practice = fixture_rows("practices")[0]
    async with app.state.sessions() as db, db.begin():
        await db.run_sync(
            lambda s: runpy.run_path(
                str(
                    Path(__file__).parents[2] / "migrations/versions/0042_simplify_machines_toys.py"
                )
            )["apply"](s.connection(), reverse=True)
        )
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        assert await db.scalar(select(func.count()).select_from(Device)) == 24
        db.add(Device(**{**custom, "description": "Custom machine description"}))
        (await db.get(Device, devices["rope"]["uid"])).description = "Custom old description"
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert await db.scalar(select(func.count()).select_from(Device)) == 48
        assert (await db.get(Device, custom["uid"])).description == "Custom machine description"
        assert (
            await db.get(Device, devices["rope"]["uid"])
        ).description == "Custom old description"
        db.add(PracticeDevice(practice_uid=practice["uid"], device_uid=linked["uid"]))
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        assert await db.get(Device, custom["uid"]) is not None
        assert await db.get(Device, linked["uid"]) is not None
        # Direct SQL migration deletes bypass the session identity map.
        assert await db.scalar(select(Device.uid).where(Device.uid == removable["uid"])) is None
        assert await db.scalar(select(func.count()).select_from(Device)) == 26
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 22
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert await db.scalar(select(func.count()).select_from(Device)) == 48
        assert (await db.get(Device, custom["uid"])).description == "Custom machine description"


async def test_device_expansion_preserves_case_insensitive_name_collisions(api):
    import json
    import runpy
    from pathlib import Path
    from uuid import uuid4

    from vowen.modules.references.models import Device

    _, app, _, _ = await seeded(api, reference_version="v13")
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0041_extra_devices.py")
    )
    v13 = json.loads(
        (
            Path(__file__).parents[2] / "src/vowen/modules/references/fixtures/v13/devices.json"
        ).read_text()
    )
    row = next(r for r in v13 if r["extra"]["code"] == "compact-sex-machine")
    row["uid"] = UUID(row["uid"])
    custom_uid = uuid4()
    async with app.state.sessions() as db, db.begin():
        await db.run_sync(
            lambda s: runpy.run_path(
                str(
                    Path(__file__).parents[2] / "migrations/versions/0042_simplify_machines_toys.py"
                )
            )["apply"](s.connection(), reverse=True)
        )
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        db.add(
            Device(
                **{
                    **row,
                    "uid": custom_uid,
                    "name": row["name"].upper(),
                    "description": "User record",
                }
            )
        )
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert await db.scalar(select(Device.uid).where(Device.uid == row["uid"])) is None
        assert (await db.get(Device, custom_uid)).description == "User record"
        assert await db.scalar(select(func.count()).select_from(Device)) == 48


async def test_machine_consolidation_moves_links_and_is_idempotent(api):
    import json
    import runpy
    from pathlib import Path

    from vowen.modules.references.models import Device, PracticeDevice

    _, app, _, _ = await seeded(api, reference_version="v14")
    root = Path(__file__).parents[2]
    migration = runpy.run_path(str(root / "migrations/versions/0042_simplify_machines_toys.py"))
    snapshot = json.loads(
        (root / "migrations/fixtures/0042-simplify-machines-toys.json").read_text()
    )
    machine_uid = UUID(snapshot["canonical"]["uid"])
    removed = [UUID(row["uid"]) for row in snapshot["removed"]]
    practice = fixture_rows("practices")[0]
    async with app.state.sessions() as db, db.begin():
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        assert await db.scalar(select(func.count()).select_from(Device)) == 48
        for uid in [machine_uid, *removed]:
            db.add(PracticeDevice(practice_uid=practice["uid"], device_uid=uid))
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert await db.scalar(select(func.count()).select_from(Device)) == 54
        assert not (await db.scalars(select(Device.uid).where(Device.uid.in_(removed)))).all()
        assert (
            await db.scalar(select(Device.name).where(Device.uid == machine_uid)) == "Секс-машина"
        )
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 22
        await seed_frozen_references(db, "v14")
        assert await db.scalar(select(func.count()).select_from(Device)) == 54
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        assert await db.scalar(select(func.count()).select_from(Device)) == 48
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 22
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert await db.scalar(select(func.count()).select_from(Device)) == 54


async def test_machine_consolidation_preserves_modified_variants_and_new_toys(api):
    import json
    import runpy
    from pathlib import Path

    from sqlalchemy import update

    from vowen.modules.references.models import Device, PracticeDevice

    _, app, _, _ = await seeded(api, reference_version="v14")
    root = Path(__file__).parents[2]
    migration = runpy.run_path(str(root / "migrations/versions/0042_simplify_machines_toys.py"))
    snapshot = json.loads(
        (root / "migrations/fixtures/0042-simplify-machines-toys.json").read_text()
    )
    variant_uid = UUID(snapshot["removed"][0]["uid"])
    toy_uid = UUID(snapshot["added"][0]["uid"])
    practice = fixture_rows("practices")[0]
    async with app.state.sessions() as db, db.begin():
        await db.execute(
            update(Device).where(Device.uid == toy_uid).values(description="User toy edit")
        )
        db.add(PracticeDevice(practice_uid=practice["uid"], device_uid=toy_uid))
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        await db.execute(
            update(Device).where(Device.uid == variant_uid).values(description="User variant edit")
        )
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert (
            await db.scalar(select(Device.description).where(Device.uid == variant_uid))
            == "User variant edit"
        )
        assert (
            await db.scalar(select(Device.description).where(Device.uid == toy_uid))
            == "User toy edit"
        )
        assert await db.scalar(select(func.count()).select_from(Device)) == 55
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 22


async def test_toy_support_expansion_preserves_edits_links_and_reseeding(api):
    import runpy
    from pathlib import Path

    from sqlalchemy import update

    from vowen.modules.references.models import Device, PracticeDevice

    _, app, _, _ = await seeded(api)
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0043_toys_supports.py")
    )
    rows = {r["extra"]["code"]: r for r in fixture_rows("devices")}
    custom = rows["glass-stimulator"]["uid"]
    linked = rows["wedge-cushion"]["uid"]
    practice = fixture_rows("practices")[0]["uid"]
    async with app.state.sessions() as db, db.begin():
        await db.execute(
            update(Device).where(Device.uid == custom).values(description="Custom glass")
        )
        await db.execute(
            update(Device)
            .where(Device.uid == rows["sex-machine"]["uid"])
            .values(description="Custom machine")
        )
        db.add(PracticeDevice(practice_uid=practice, device_uid=linked))
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection(), reverse=True))
        assert await db.scalar(select(func.count()).select_from(Device)) == 56
        assert (
            await db.scalar(select(Device.description).where(Device.uid == custom))
            == "Custom glass"
        )
        assert await db.scalar(select(Device.uid).where(Device.uid == linked)) == linked
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        await seed_references(db)
        assert await db.scalar(select(func.count()).select_from(Device)) == 62
        assert (
            await db.scalar(
                select(Device.description).where(Device.uid == rows["sex-machine"]["uid"])
            )
            == "Custom machine"
        )
        assert (
            await db.scalar(select(Device.description).where(Device.uid == custom))
            == "Custom glass"
        )
        assert await db.scalar(select(func.count()).select_from(PracticeDevice)) == 22


async def test_toy_support_expansion_preserves_name_collisions(api):
    import runpy
    from pathlib import Path
    from uuid import uuid4

    from vowen.modules.references.models import Device

    _, app, _, _ = await seeded(api, reference_version="v14")
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0043_toys_supports.py")
    )
    row = next(r for r in fixture_rows("devices") if r["extra"]["code"] == "bolster-cushion")
    custom_uid = uuid4()
    async with app.state.sessions() as db, db.begin():
        db.add(
            Device(
                **{
                    **row,
                    "uid": custom_uid,
                    "name": row["name"].upper(),
                    "description": "User bolster",
                }
            )
        )
        await db.flush()
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        await db.run_sync(lambda s: migration["apply"](s.connection()))
        assert await db.scalar(select(Device.uid).where(Device.uid == row["uid"])) is None
        assert (
            await db.scalar(select(Device.description).where(Device.uid == custom_uid))
            == "User bolster"
        )
        assert await db.scalar(select(func.count()).select_from(Device)) == 62
