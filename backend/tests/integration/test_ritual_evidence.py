import base64
from datetime import timedelta
from uuid import uuid4

from conftest import NOW
from sqlalchemy import text
from test_ritual_review import setup_ritual
from test_sessions import auth, login
from test_telegram_validation import signed

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jS1sAAAAASUVORK5CYII="
)


async def assignment(client, token, template, recipient, required=True):
    response = await client.post(
        f"/api/v1/rituals/{template['id']}/assignments",
        headers=auth(token),
        json={
            "idempotency_key": str(uuid4()),
            "recipient_id": str(recipient),
            "reviewer_ids": [],
            "approval_required": False,
            "evidence_policy": {"required": required, "allowed_types": ["link", "photo", "video"]},
            "schedule": {
                "kind": "daily",
                "timezone": "UTC",
                "hour": 9,
                "minute": 0,
                "start_date": "2026-10-15",
            },
        },
    )
    assert response.status_code == 200
    return response.json()


async def test_required_evidence_is_bound_to_immutable_report_attempt_and_current_acl(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    a = await assignment(client, tokens[0], template, ids[1])
    o = next(
        r
        for r in (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
        if r["assignment_id"] == a["id"]
    )
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    command = {
        "expected_version": o["revision"],
        "idempotency_key": str(uuid4()),
        "text": "With proof",
    }
    assert (
        await client.post(path + "/report", headers=auth(tokens[1]), json=command)
    ).status_code == 422
    upload = {
        "idempotency_key": str(uuid4()),
        "kind": "photo",
        "media_type": "image/png",
        "data_base64": base64.b64encode(PNG).decode(),
    }
    bad = await client.post(path + "/evidence", headers=auth(tokens[0]), json=upload)
    assert bad.status_code in (403, 404)
    response = await client.post(path + "/evidence", headers=auth(tokens[1]), json=upload)
    assert response.status_code == 200
    proof = response.json()
    staged = await client.get(path + "/evidence", headers=auth(tokens[1]))
    assert staged.status_code == 200 and [x["id"] for x in staged.json()] == [proof["id"]]
    assert (await client.get(path + "/evidence", headers=auth(tokens[0]))).status_code == 404

    assert (await client.post(path + "/evidence", headers=auth(tokens[1]), json=upload)).json()[
        "id"
    ] == proof["id"]
    command.update(evidence_ids=[proof["id"]], links=["https://example.org/private-proof"])
    sent = await client.post(path + "/report", headers=auth(tokens[1]), json=command)
    assert (
        sent.status_code == 200 and sent.json()["reports"][0]["attachments"][0]["id"] == proof["id"]
    )
    assert (
        await client.post(path + "/report", headers=auth(tokens[1]), json=command)
    ).status_code == 200
    command["links"] = []
    assert (
        await client.post(path + "/report", headers=auth(tokens[1]), json=command)
    ).status_code == 409
    download = f"/api/v1/ritual-evidence/{proof['id']}"
    body = (await client.get(download, headers=auth(tokens[1]))).json()
    assert base64.b64decode(body["data_base64"]) == PNG
    # Issuer of auto-approved assignment is not a report reader.
    assert (await client.get(download, headers=auth(tokens[0]))).status_code == 404
    assert (await client.get(download, headers=auth(tokens[3]))).status_code == 404
    async with app.state.engine.connect() as conn:
        stored = (
            await conn.execute(
                text("SELECT ciphertext FROM ritual_evidence WHERE id=:id"), {"id": proof["id"]}
            )
        ).scalar_one()
        assert PNG not in stored


async def test_evidence_rejects_active_content_cross_occurrence_and_unsafe_links(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    upload = {
        "idempotency_key": str(uuid4()),
        "kind": "photo",
        "media_type": "image/png",
        "data_base64": base64.b64encode(b'<svg onload="evil()"/>').decode(),
    }
    assert (
        await client.post(path + "/evidence", headers=auth(tokens[1]), json=upload)
    ).status_code == 422
    upload["data_base64"] = base64.b64encode(PNG).decode()
    proof = (await client.post(path + "/evidence", headers=auth(tokens[1]), json=upload)).json()
    a2 = await assignment(client, tokens[0], template, ids[1], False)
    o2 = next(
        r
        for r in (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
        if r["assignment_id"] == a2["id"]
    )
    body = {
        "expected_version": o2["revision"],
        "idempotency_key": str(uuid4()),
        "text": "Wrong proof",
        "evidence_ids": [proof["id"]],
    }
    assert (
        await client.post(
            f"/api/v1/ritual-occurrences/{o2['id']}/report", headers=auth(tokens[1]), json=body
        )
    ).status_code == 422
    body["evidence_ids"] = []
    body["links"] = ["javascript:alert(1)"]
    assert (
        await client.post(
            f"/api/v1/ritual-occurrences/{o2['id']}/report", headers=auth(tokens[1]), json=body
        )
    ).status_code == 422
    async with app.state.sessions() as db, db.begin():
        from vowen.core.maintenance import prune_expired

        await prune_expired(db, NOW + timedelta(days=2))
    tokens[1] = (await login(client, signed(100000000002, query_id=str(uuid4())))).json()
    assert (
        await client.get(f"/api/v1/ritual-evidence/{proof['id']}", headers=auth(tokens[1]))
    ).status_code == 404


async def test_evidence_quotas_video_and_reviewer_withdrawal(api):
    import asyncio

    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    path = f"/api/v1/ritual-occurrences/{o['id']}"
    upload = {
        "kind": "video",
        "media_type": "video/mp4",
        "data_base64": base64.b64encode(b"\x00\x00\x00\x14ftypisom\x00\x00\x00\x00isom").decode(),
    }
    responses = await asyncio.gather(
        *(
            client.post(
                path + "/evidence",
                headers=auth(tokens[1]),
                json={**upload, "idempotency_key": str(uuid4())},
            )
            for _ in range(4)
        )
    )
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 413]
    eid = next(r.json()["id"] for r in responses if r.status_code == 200)
    report = await client.post(
        path + "/report",
        headers=auth(tokens[1]),
        json={
            "expected_version": o["revision"],
            "idempotency_key": str(uuid4()),
            "text": "Private video",
            "evidence_ids": [eid],
        },
    )
    assert report.status_code == 200
    download = f"/api/v1/ritual-evidence/{eid}"
    assert (await client.get(download, headers=auth(tokens[0]))).status_code == 200
    relation = (await client.get("/api/v1/relations", headers=auth(tokens[0]))).json()[0]
    assert (
        await client.post(
            f"/api/v1/relations/{relation['id']}/pause",
            headers=auth(tokens[0]),
            json={"expected_version": relation["version"]},
        )
    ).status_code == 200
    assert (await client.get(download, headers=auth(tokens[0]))).status_code == 404
    assert (await client.get(download, headers=auth(tokens[1]))).status_code == 200
    # A public/non-member request cannot consume a large JSON body at an unrelated endpoint.
    assert (await client.post("/api/v1/auth/telegram", content=b"x" * 524289)).status_code == 413


async def test_decoded_media_limit_cannot_be_bypassed_by_base64(api):
    client, app, ids, tokens, template, a, o = await setup_ritual(api)
    response = await client.post(
        f"/api/v1/ritual-occurrences/{o['id']}/evidence",
        headers=auth(tokens[1]),
        json={
            "idempotency_key": str(uuid4()),
            "kind": "photo",
            "media_type": "image/png",
            "data_base64": base64.b64encode(
                b"\x89PNG\r\n\x1a\n" + b"x" * (8 * 1024 * 1024 - 7)
            ).decode(),
        },
    )
    assert response.status_code == 413
