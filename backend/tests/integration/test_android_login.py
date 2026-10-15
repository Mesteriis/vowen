import asyncio
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from conftest import NOW
from sqlalchemy import func, select
from test_sessions import auth, provision

from vowen.core.errors import AppError
from vowen.modules.auth.android_challenge import decide_challenge, present_challenge
from vowen.modules.auth.models import Session
from vowen.modules.identity.models import User


async def challenge(client):
    nonce = secrets.token_urlsafe(32)
    result = await client.post(
        "/api/v1/auth/android/challenges",
        json={"client_nonce": nonce, "device_label": "Synthetic Android"},
    )
    assert result.status_code == 200
    body = result.json()
    start = parse_qs(urlparse(body["bot_url"]).query)["start"][0]
    assert len(start) <= 64
    return body, nonce, start[6:]


async def test_start_is_not_approval_wrong_actor_and_atomic_consume(api):
    client, app = api
    await provision(app)
    await provision(app, 100000000002)
    created, nonce, start = await challenge(client)
    base = "/api/v1/auth/android/challenges/" + created["challenge_id"]
    proof = {"poll_secret": created["poll_secret"], "client_nonce": nonce}
    assert (await client.post(base + "/status", json=proof)).json()["status"] == "pending"
    async with app.state.sessions() as db:
        presented = await present_challenge(db, start, 100000000001, NOW)
        await db.commit()
        assert presented.display_code == created["display_code"]
    assert (await client.post(base + "/consume", json=proof)).status_code == 409
    async with app.state.sessions() as db:
        with pytest.raises(AppError):
            await decide_challenge(db, presented.id, 100000000002, True, NOW)
        await db.rollback()
        await decide_challenge(db, presented.id, 100000000001, True, NOW)
        await db.commit()
        # Duplicate callback has no repeated effect.
        await decide_challenge(db, presented.id, 100000000001, True, NOW)
        await db.commit()
    assert (
        await client.post(base + "/status", json={**proof, "poll_secret": start})
    ).status_code == 401
    assert (
        await client.post(
            base + "/consume", json={**proof, "client_nonce": secrets.token_urlsafe(32)}
        )
    ).status_code == 401
    responses = await asyncio.gather(
        client.post(base + "/consume", json=proof), client.post(base + "/consume", json=proof)
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    good = next(r.json() for r in responses if r.status_code == 200)
    assert (await client.get("/api/v1/me", headers=auth(good))).status_code == 200
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Session)) == 1


@pytest.mark.parametrize("decision", ["reject", "expire", "disable", "unknown"])
async def test_rejected_expired_disabled_unknown_never_issue_session(api, decision):
    client, app = api
    if decision != "unknown":
        await provision(app)
    created, nonce, start = await challenge(client)
    async with app.state.sessions() as db:
        if decision == "unknown":
            with pytest.raises(AppError):
                await present_challenge(db, start, 100000000001, NOW)
        else:
            presented = await present_challenge(db, start, 100000000001, NOW)
            await decide_challenge(db, presented.id, 100000000001, decision != "reject", NOW)
            if decision == "disable":
                user = await db.scalar(select(User))
                user.is_active = False
            await db.commit()
    if decision == "expire":
        app.state.clock = type(
            "FutureClock", (), {"now": lambda self: NOW + timedelta(seconds=301)}
        )()
    result = await client.post(
        "/api/v1/auth/android/challenges/" + created["challenge_id"] + "/consume",
        json={"poll_secret": created["poll_secret"], "client_nonce": nonce},
    )
    assert result.status_code != 200
    async with app.state.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Session)) == 0
        assert await db.scalar(select(func.count()).select_from(User)) == (
            0 if decision == "unknown" else 1
        )
