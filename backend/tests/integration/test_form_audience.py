from datetime import timedelta
from uuid import uuid4

from conftest import NOW
from sqlalchemy import select
from test_forms_versions import setup_forms

from vowen.modules.forms.models import Submission


async def test_reader_removal_plain_storage_and_no_author_inheritance(api):
    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    invite = (
        await c.post(
            p + "/invitations",
            headers=h[0],
            json={"recipient_user_id": str(ids[1]), "reader_ids": [str(ids[2])]},
        )
    ).json()
    ip = "/api/v1/form-invitations/" + invite["id"]
    await c.put(ip + "/draft", headers=h[1], json={"answers": {"q": "plaintext must not persist"}})
    async with app.state.sessions() as db:
        row = await db.scalar(select(Submission))
        assert row.ciphertext and b"plaintext" in row.ciphertext
        assert row.idempotency_key is None
    result = await c.post(
        ip + "/submit",
        headers=h[1],
        json={
            "answers": {"q": "private final"},
            "idempotency_key": str(uuid4()),
            "acknowledged": True,
        },
    )
    sid = result.json()["id"]
    assert (await c.get("/api/v1/form-submissions/" + sid, headers=h[0])).status_code == 404
    assert (await c.get("/api/v1/form-submissions/" + sid, headers=h[2])).status_code == 200
    assert (
        await c.delete(
            "/api/v1/forms/invitations/" + invite["id"] + "/readers/" + str(ids[2]), headers=h[0]
        )
    ).status_code == 204
    assert (await c.get("/api/v1/form-submissions/" + sid, headers=h[2])).status_code == 404
    assert (await c.get("/api/v1/form-submissions/" + sid, headers=h[1])).status_code == 200
    assert (await c.patch(ip, headers=h[1], json={"reader_ids": [str(ids[0])]})).status_code in (
        404,
        405,
    )
    await c.delete("/api/v1/form-submissions/" + sid, headers=h[1])
    async with app.state.sessions() as db:
        row = await db.get(Submission, sid)
        assert row.ciphertext is None and row.nonce is None and row.key_id is None


async def test_retention_prunes_payload_and_guest_rate_limits(api):
    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    i = (
        await c.post(
            p + "/invitations",
            headers=h[0],
            json={"recipient_user_id": str(ids[1]), "reader_ids": [], "retention_days": 1},
        )
    ).json()
    await c.put(
        "/api/v1/form-invitations/" + i["id"] + "/draft",
        headers=h[1],
        json={"answers": {"q": "draft"}},
    )
    from vowen.core.maintenance import prune_expired

    async with app.state.sessions() as db, db.begin():
        await prune_expired(db, NOW + timedelta(days=8))
    async with app.state.sessions() as db:
        row = await db.scalar(select(Submission))
        assert row.ciphertext is None
    statuses = []
    for _ in range(22):
        r = await c.post(
            "/api/v1/guest/invitations/exchange",
            headers={"Origin": "https://test"},
            json={"public_id": str(uuid4()), "token": "a" * 43},
        )
        statuses.append(r.status_code)
    assert 429 in statuses


async def test_retention_starts_at_submission_not_invitation_and_does_not_expire_draft_early(api):
    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    i = (
        await c.post(
            p + "/invitations",
            headers=h[0],
            json={"recipient_user_id": str(ids[1]), "reader_ids": [], "retention_days": 1},
        )
    ).json()
    app.state.clock = type("Clock", (), {"now": lambda self: NOW + timedelta(days=6)})()
    from test_sessions import auth, login
    from test_telegram_validation import signed

    fresh = auth((await login(c, signed(100000000002, offset=6 * 86400))).json())
    ip = "/api/v1/form-invitations/" + i["id"]
    draft = await c.put(ip + "/draft", headers=fresh, json={"answers": {"q": "day six"}})
    assert draft.status_code == 200
    assert draft.json()["retention_until"] is None
    submitted = await c.post(
        ip + "/submit",
        headers=fresh,
        json={"answers": {"q": "day six"}, "idempotency_key": str(uuid4()), "acknowledged": True},
    )
    assert submitted.status_code == 200
    final = (await c.get(ip, headers=fresh)).json()
    assert final["retention_until"] == (NOW + timedelta(days=7)).isoformat()
    assert final["retention_days"] == 1
