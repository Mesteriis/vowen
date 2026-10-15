import asyncio

import pytest
from test_sessions import auth, login, provision
from test_telegram_validation import signed


async def test_profile_updates_are_private_persisted_and_work_during_pause(api):
    client, app = api
    await provision(app)
    await provision(app, 100000000002)
    tokens = (await login(client)).json()
    other = (await login(client, signed(100000000002))).json()
    initial = (await client.get("/api/v1/me", headers=auth(tokens))).json()
    assert initial["language"] == "en"
    assert initial["timezone"] == "UTC"
    assert initial["profile_labels"] == []
    await client.post("/api/v1/me/pause", headers=auth(tokens))
    updated = await client.patch(
        "/api/v1/me/preferences",
        headers=auth(tokens),
        json={
            "expected_version": initial["profile_version"],
            "display_name": " New name ",
            "language": "ru",
            "timezone": "Europe/Madrid",
            "profile_labels": ["switch"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "New name"
    assert updated.json()["paused"] is True
    assert updated.json()["profile_version"] == 2
    assert (await client.get("/api/v1/me", headers=auth(tokens))).json() == updated.json()
    assert (await client.get("/api/v1/me", headers=auth(other))).json()["language"] == "en"
    participants = (await client.get("/api/v1/participants", headers=auth(other))).json()
    assert set(participants[0]) == {"id", "display_name", "profile_labels"}
    assert "Europe/Madrid" not in str(participants)


@pytest.mark.parametrize(
    "payload",
    [
        {"telegram_id": 123},
        {"is_active": False},
        {"user_id": "00000000-0000-0000-0000-000000000001"},
        {"display_name": "  "},
        {"language": "xx"},
        {"timezone": "../etc/passwd"},
        {"profile_labels": ["admin"]},
        {"profile_labels": ["dominant", "dominant"]},
        {"language": None},
    ],
)
async def test_invalid_or_privileged_profile_mutations_are_rejected(api, payload):
    client, app = api
    await provision(app)
    tokens = (await login(client)).json()
    response = await client.patch(
        "/api/v1/me/preferences", headers=auth(tokens), json={"expected_version": 1, **payload}
    )
    assert response.status_code == 422
    assert (await client.get("/api/v1/me", headers=auth(tokens))).json()[
        "display_name"
    ] == "Synthetic"


async def test_profile_concurrency_and_authentication(api):
    client, app = api
    await provision(app)
    tokens = (await login(client)).json()
    assert (
        await client.patch("/api/v1/me/preferences", json={"expected_version": 1, "language": "ru"})
    ).status_code == 401
    replies = await asyncio.gather(
        *[
            client.patch(
                "/api/v1/me/preferences",
                headers=auth(tokens),
                json={"expected_version": 1, "display_name": name},
            )
            for name in ("First", "Second")
        ]
    )
    assert sorted(r.status_code for r in replies) == [200, 409]
    assert (await client.get("/api/v1/me", headers=auth(tokens))).json()["profile_version"] == 2


async def test_profile_labels_never_grant_authority(api):
    from uuid import UUID

    from vowen.core.errors import AppError
    from vowen.modules.auth.service import MemberPrincipal
    from vowen.modules.relations.policy import ResourceContext, authorize

    client, app = api
    own = await provision(app)
    target = await provision(app, 100000000002)
    tokens = (await login(client)).json()
    updated = await client.patch(
        "/api/v1/me/preferences",
        headers=auth(tokens),
        json={"expected_version": 1, "profile_labels": ["dominant"]},
    )
    assert updated.status_code == 200
    async with app.state.sessions() as db:
        with pytest.raises(AppError):
            await authorize(
                db,
                MemberPrincipal(own, UUID(tokens["session_id"])),
                "rules.assign",
                ResourceContext(target, frozenset({own})),
            )
