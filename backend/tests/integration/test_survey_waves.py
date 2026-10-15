import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from conftest import NOW
from sqlalchemy import text
from test_forms_versions import SCHEMA, setup_forms


async def setup(api):
    c, app, ids, h, f = await setup_forms(api)
    f = (
        await c.post(
            "/api/v1/forms/" + f["id"] + "/publish", headers=h[0], json={"expected_version": 1}
        )
    ).json()
    body = {
        "form_version_id": f["version_id"],
        "recipient_id": str(ids[1]),
        "reader_ids": [str(ids[0])],
        "schedule": {
            "kind": "daily",
            "timezone": "UTC",
            "hour": 10,
            "minute": 0,
            "start_date": "2026-10-15",
            "window_hours": 24,
        },
        "idempotency_key": str(uuid4()),
    }
    response = await c.post("/api/v1/survey-schedules", headers=h[0], json=body)
    assert response.status_code == 200
    return c, app, ids, h, f, response.json(), body


async def generate(app, now):
    from vowen.core.crypto import PayloadCipher
    from vowen.modules.surveys.service import generate

    async with app.state.sessions() as db, db.begin():
        await generate(db, now, PayloadCipher(app.state.settings.data_keyring_file), "https://test")


async def test_repeat_versions_answers_and_concurrent_worker(api):
    c, app, ids, h, f, p, body = await setup(api)
    await asyncio.gather(generate(app, NOW), generate(app, NOW))
    waves = (await c.get(f"/api/v1/survey-schedules/{p['id']}/waves", headers=h[0])).json()
    assert len(waves) == 1 and waves[0]["status"] == "created"
    first = waves[0]["invitation_id"]
    assert (
        await c.post(
            f"/api/v1/form-invitations/{first}/submit",
            headers=h[1],
            json={
                "answers": {"q": "original-answer"},
                "idempotency_key": str(uuid4()),
                "acknowledged": True,
            },
        )
    ).status_code == 200
    newer = (
        await c.post(
            f"/api/v1/forms/{f['id']}/versions",
            headers=h[0],
            json={
                "expected_version": f["revision"],
                "schema_body": {**SCHEMA, "title": "Replacement form"},
            },
        )
    ).json()
    await c.post(
        f"/api/v1/forms/{f['id']}/publish",
        headers=h[0],
        json={"expected_version": newer["revision"]},
    )
    await asyncio.gather(
        generate(app, NOW + timedelta(days=1)), generate(app, NOW + timedelta(days=1))
    )
    waves = (await c.get(f"/api/v1/survey-schedules/{p['id']}/waves", headers=h[1])).json()
    assert len(waves) == 2 and len({w["invitation_id"] for w in waves}) == 2
    responses = (await c.get("/api/v1/form-submissions", headers=h[0])).json()
    assert responses[0]["answers"] == {"q": "original-answer"}
    async with app.state.engine.connect() as conn:
        assert (
            await conn.execute(text("SELECT count(DISTINCT version_id) FROM form_invitations"))
        ).scalar_one() == 1
    assert (await c.get("/api/v1/survey-schedules", headers=h[2])).json() == []
    assert (
        await c.get(f"/api/v1/survey-schedules/{p['id']}/waves", headers=h[2])
    ).status_code == 404


async def test_recipient_pause_cannot_be_overridden_and_downtime_skips_expired(api):
    c, app, ids, h, f, p, _ = await setup(api)
    p = (
        await c.post(
            f"/api/v1/survey-schedules/{p['id']}/pause",
            headers=h[1],
            json={"expected_version": p["revision"]},
        )
    ).json()
    assert p["recipient_paused"] is True
    assert (
        await c.post(
            f"/api/v1/survey-schedules/{p['id']}/resume",
            headers=h[0],
            json={"expected_version": p["revision"]},
        )
    ).status_code == 409
    await generate(app, NOW + timedelta(days=1))
    p = (
        await c.post(
            f"/api/v1/survey-schedules/{p['id']}/resume",
            headers=h[1],
            json={"expected_version": p["revision"]},
        )
    ).json()
    await generate(app, NOW + timedelta(days=5))
    waves = (await c.get(f"/api/v1/survey-schedules/{p['id']}/waves", headers=h[0])).json()
    assert any(w["reason"] == "expired" for w in waves)
    assert (
        sum(w["status"] == "created" for w in waves) == 2
    )  # first and current, never old expired slots


async def test_manual_wave_retries_and_immutable_configuration(api):
    c, app, ids, h, f, p, body = await setup(api)
    assert (await c.post("/api/v1/survey-schedules", headers=h[0], json=body)).json()["id"] == p[
        "id"
    ]
    assert (
        await c.post("/api/v1/survey-schedules", headers=h[0], json={**body, "reader_ids": []})
    ).status_code == 409
    manual = {"expected_version": p["revision"], "idempotency_key": str(uuid4())}
    path = f"/api/v1/survey-schedules/{p['id']}/send-now"
    assert (await c.post(path, headers=h[1], json=manual)).status_code == 403
    outcomes = await asyncio.gather(*(c.post(path, headers=h[0], json=manual) for _ in range(2)))
    assert all(x.status_code == 200 for x in outcomes)
    assert outcomes[0].json()["id"] == outcomes[1].json()["id"]
    assert (
        await c.patch(
            f"/api/v1/survey-schedules/{p['id']}", headers=h[1], json={"reader_ids": [str(ids[2])]}
        )
    ).status_code in (404, 405)


@pytest.mark.parametrize("revocation", [None, "relation", "assignment", "pause"])
async def test_feedback_once_after_approval_and_current_source_authority(api, revocation):
    from test_ritual_review import setup_ritual
    from test_sessions import auth

    c, app, ids, tokens, _, a, o = await setup_ritual(api)
    h = [auth(t) for t in tokens]
    f = (await c.post("/api/v1/forms", headers=h[0], json=SCHEMA)).json()
    f = (
        await c.post(f"/api/v1/forms/{f['id']}/publish", headers=h[0], json={"expected_version": 1})
    ).json()
    from vowen.modules.forms.models import BotContact

    async with app.state.sessions() as db, db.begin():
        db.add(BotContact(telegram_id=100000000002, allowed=True))
    response = await c.post(
        "/api/v1/survey-schedules",
        headers=h[0],
        json={
            "form_version_id": f["version_id"],
            "recipient_id": str(ids[1]),
            "reader_ids": [],
            "ritual_assignment_id": a["id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert response.status_code == 200
    p = response.json()
    await generate(app, NOW)
    assert (await c.get(f"/api/v1/survey-schedules/{p['id']}/waves", headers=h[0])).json() == []
    o = (
        await c.post(
            f"/api/v1/ritual-occurrences/{o['id']}/report",
            headers=h[1],
            json={
                "expected_version": o["revision"],
                "idempotency_key": str(uuid4()),
                "text": "Synthetic report",
            },
        )
    ).json()
    assert (
        await c.post(
            f"/api/v1/ritual-occurrences/{o['id']}/review",
            headers=h[0],
            json={"expected_version": o["revision"], "decision": "approved"},
        )
    ).status_code == 200
    if revocation:
        async with app.state.sessions() as db, db.begin():
            statement = {
                "relation": "UPDATE authority_relations SET status='revoked',version=version+1",
                "assignment": "UPDATE ritual_assignments SET revision=revision+1",
                "pause": "UPDATE users SET paused=true",
            }[revocation]
            await db.execute(text(statement))
    await asyncio.gather(generate(app, NOW), generate(app, NOW))
    waves = (await c.get(f"/api/v1/survey-schedules/{p['id']}/waves", headers=h[0])).json()
    assert len(waves) == 1 and waves[0]["occurrence_id"] == o["id"]
    assert waves[0]["status"] == ("skipped" if revocation else "created")
    if not revocation:
        from uuid import UUID

        from sqlalchemy import select

        from vowen.modules.forms.delivery import available_at
        from vowen.modules.forms.models import Delivery

        # Check the actual survey outbox against rights revoked after wave creation.
        async with app.state.sessions() as db, db.begin():
            delivery = await db.scalar(
                select(Delivery).where(Delivery.invitation_id == UUID(waves[0]["invitation_id"]))
            )
            assert delivery is not None
            await db.execute(text("UPDATE authority_relations SET status='revoked'"))
            assert await available_at(db, delivery, NOW) is None


@pytest.mark.parametrize(
    "day,first,second,expected",
    [
        (
            "2026-10-25",
            "2026-10-25T00:35:00+00:00",
            "2026-10-25T01:35:00+00:00",
            "2026-10-25T00:30:00Z",
        ),
        (
            "2027-03-28",
            "2027-03-28T01:35:00+00:00",
            "2027-03-28T02:35:00+00:00",
            "2027-03-28T01:30:00Z",
        ),
    ],
)
async def test_survey_dst_has_one_local_wave(api, day, first, second, expected):
    from datetime import datetime

    c, app, _, h, f, _, body = await setup(api)
    body.update(
        idempotency_key=str(uuid4()),
        schedule={
            "kind": "weekly",
            "timezone": "Europe/Madrid",
            "hour": 2,
            "minute": 30,
            "start_date": day,
            "weekdays": [6],
            "window_hours": 24,
        },
    )
    response = await c.post("/api/v1/survey-schedules", headers=h[0], json=body)
    assert response.status_code == 200
    pid = response.json()["id"]
    await generate(app, datetime.fromisoformat(first))
    await generate(app, datetime.fromisoformat(second))
    waves = (await c.get(f"/api/v1/survey-schedules/{pid}/waves", headers=h[0])).json()
    assert len(waves) == 1 and waves[0]["due_at"] == expected


async def test_archived_version_blocks_waves_and_client_source_state(api):
    c, app, _, h, f, plan, _ = await setup(api)
    await c.post(
        f"/api/v1/forms/{f['id']}/archive", headers=h[0], json={"expected_version": f["revision"]}
    )
    await generate(app, NOW + timedelta(days=1))
    waves = (await c.get(f"/api/v1/survey-schedules/{plan['id']}/waves", headers=h[0])).json()
    plans = (await c.get("/api/v1/survey-schedules", headers=h[0])).json()
    assert next(p for p in plans if p["id"] == plan["id"])["source_effective"] is False
    assert waves[-1]["reason"] == "source_unavailable"
    assert sum(w["status"] == "created" for w in waves) == 1


async def test_paused_selected_reader_skips_wave_without_changing_audience(api):
    c, app, ids, h, _, _, body = await setup(api)
    body.update(idempotency_key=str(uuid4()), reader_ids=[str(ids[2])])
    response = await c.post("/api/v1/survey-schedules", headers=h[0], json=body)
    assert response.status_code == 200
    plan = response.json()
    async with app.state.sessions() as db, db.begin():
        await db.execute(text("UPDATE users SET paused=true WHERE id=:id"), {"id": ids[2]})
    await generate(app, NOW + timedelta(days=1))
    waves = (await c.get(f"/api/v1/survey-schedules/{plan['id']}/waves", headers=h[0])).json()
    assert waves[-1]["reason"] == "audience_unavailable"
    plans = (await c.get("/api/v1/survey-schedules", headers=h[0])).json()
    assert next(p for p in plans if p["id"] == plan["id"])["reader_ids"] == [str(ids[2])]
