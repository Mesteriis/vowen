from datetime import timedelta

from conftest import NOW
from sqlalchemy import text
from test_member_delivery import enqueue_assignment
from test_sessions import auth


async def preferences(client, token, **changes):
    current = await client.get("/api/v1/me/notifications", headers=auth(token))
    assert current.status_code == 200
    body = {
        k: v
        for k, v in current.json().items()
        if k not in ("revision", "timezone", "telegram_connected")
    }
    return await client.patch(
        "/api/v1/me/notifications",
        headers=auth(token),
        json={**body, **changes, "expected_version": current.json()["revision"]},
    )


async def test_channels_do_not_opt_in_bot_or_grant_access(api):
    client, app, ids, tokens, _ = await enqueue_assignment(api)
    settings = await client.get("/api/v1/me/notifications", headers=auth(tokens[1]))
    assert settings.status_code == 200
    assert settings.json()["channels"] == ["in_app", "telegram"]
    assert (await preferences(client, tokens[1], channels=[])).status_code == 200
    assert (await client.get("/api/v1/ritual-notices", headers=auth(tokens[1]))).json() == []
    from vowen.modules.notifications.delivery import claim

    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None
        assert (
            await db.execute(text("SELECT count(*) FROM member_deliveries WHERE status='pending'"))
        ).scalar_one() == 0
    # Turning the app channel on does not resurrect cancelled deliveries.
    assert (
        await preferences(client, tokens[1], channels=["in_app", "telegram"])
    ).status_code == 200
    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None
    assert len((await client.get("/api/v1/ritual-notices", headers=auth(tokens[1]))).json()) > 0


async def test_quiet_hours_defer_without_attempt_and_recheck_after_claim(api):
    client, app, ids, tokens, _ = await enqueue_assignment(api)
    assert (
        await preferences(
            client, tokens[1], quiet_enabled=True, quiet_start=9 * 60, quiet_end=11 * 60
        )
    ).status_code == 200
    from vowen.modules.notifications.delivery import claim, prepare

    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None
        assert (
            await db.execute(text("SELECT max(attempts) FROM member_deliveries"))
        ).scalar_one() == 0
        rows = (
            (
                await db.execute(
                    text("SELECT available_at FROM member_deliveries WHERE status='pending'")
                )
            )
            .scalars()
            .all()
        )
        assert rows and all(t == NOW + timedelta(hours=1) for t in rows)
    later = NOW + timedelta(hours=1)
    async with app.state.sessions() as db, db.begin():
        task = await claim(db, later)
    assert task
    assert (await preferences(client, tokens[1], quiet_end=12 * 60)).status_code == 200
    async with app.state.sessions() as db, db.begin():
        assert await prepare(db, task, later) is None
        assert (
            await db.execute(
                text("SELECT attempts FROM member_deliveries WHERE id=:id"), {"id": task.id}
            )
        ).scalar_one() == 0


async def test_off_on_generation_fences_an_uncommitted_event(api):
    from uuid import UUID, uuid4

    from vowen.modules.notifications.delivery import claim, enqueue
    from vowen.modules.rituals.models import RitualNotice

    client, app, ids, tokens, assignment = await enqueue_assignment(api)
    # The new outbox is invisible to channel-off cancellation, then commits
    # after off/on. Its captured generation must still fence the stale event.
    async with app.state.sessions() as db, db.begin():
        notice = RitualNotice(
            id=uuid4(),
            assignment_id=UUID(assignment["id"]),
            user_id=ids[1],
            event_key="test:" + str(uuid4()),
            kind="assigned",
            created_at=NOW,
        )
        db.add(notice)
        await db.flush()
        await enqueue(db, ids[1], NOW, ritual_notice_id=notice.id)
        await preferences(client, tokens[1], channels=["in_app"])
        await preferences(client, tokens[1], channels=["in_app", "telegram"])
    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None


async def test_invalid_quiet_config_and_optimistic_settings(api):
    client, _, _, tokens, _ = await enqueue_assignment(api)
    initial = (await client.get("/api/v1/me/notifications", headers=auth(tokens[1]))).json()
    assert "revision" in initial
    body = {
        "expected_version": initial["revision"],
        "channels": ["telegram"],
        "quiet_enabled": True,
        "quiet_start": 600,
        "quiet_end": 600,
    }
    assert (
        await client.patch("/api/v1/me/notifications", headers=auth(tokens[1]), json=body)
    ).status_code == 422
    body["quiet_end"] = 660
    assert (
        await client.patch("/api/v1/me/notifications", headers=auth(tokens[1]), json=body)
    ).status_code == 200
    assert (
        await client.patch("/api/v1/me/notifications", headers=auth(tokens[1]), json=body)
    ).status_code == 409


async def test_form_delivery_honors_channel_and_quiet_hours(api):
    from test_forms_versions import setup_forms

    from vowen.core.crypto import PayloadCipher
    from vowen.modules.forms.delivery import claim_delivery
    from vowen.modules.forms.models import BotContact

    c, app, ids, h, f = await setup_forms(api)
    await c.post(
        "/api/v1/forms/" + f["id"] + "/publish", headers=h[0], json={"expected_version": 1}
    )
    async with app.state.sessions() as db, db.begin():
        db.add(BotContact(telegram_id=100000000002, allowed=True))
    body = {"recipient_user_id": str(ids[1]), "reader_ids": [], "deliver": True}
    invite = await c.post("/api/v1/forms/" + f["id"] + "/invitations", headers=h[0], json=body)
    assert invite.json()["delivery_status"] == "pending"
    settings = (await c.get("/api/v1/me/notifications", headers=h[1])).json()

    async def change(**extra):
        nonlocal settings
        response = await c.patch(
            "/api/v1/me/notifications",
            headers=h[1],
            json={
                "expected_version": settings["revision"],
                "channels": ["in_app", "telegram"],
                "quiet_enabled": True,
                "quiet_start": 540,
                "quiet_end": 660,
                **extra,
            },
        )
        assert response.status_code == 200
        settings = response.json()

    await change()
    async with app.state.sessions() as db, db.begin():
        assert (
            await claim_delivery(db, NOW, PayloadCipher(app.state.settings.data_keyring_file))
            is None
        )
    await change(channels=["in_app"])
    await change(channels=["in_app", "telegram"], quiet_enabled=False)
    async with app.state.sessions() as db, db.begin():
        assert (
            await claim_delivery(
                db, NOW + timedelta(hours=1), PayloadCipher(app.state.settings.data_keyring_file)
            )
            is None
        )


async def test_settings_cannot_create_or_enable_a_bot_contact(api):
    from test_forms_versions import setup_forms

    c, app, _, h, _ = await setup_forms(api)
    settings = (await c.get("/api/v1/me/notifications", headers=h[1])).json()
    assert settings["telegram_connected"] is False
    result = await c.patch(
        "/api/v1/me/notifications",
        headers=h[1],
        json={
            "expected_version": settings["revision"],
            "channels": ["telegram"],
            "quiet_enabled": False,
            "quiet_start": 1320,
            "quiet_end": 480,
        },
    )
    assert result.status_code == 200 and result.json()["telegram_connected"] is False
    async with app.state.sessions() as db:
        assert (await db.execute(text("SELECT count(*) FROM bot_contacts"))).scalar_one() == 0


async def test_form_quiet_change_rechecks_a_claim_and_reschedules_without_attempt(api):
    from test_forms_versions import setup_forms

    from vowen.core.crypto import PayloadCipher
    from vowen.modules.forms.delivery import claim_delivery, prepare_delivery
    from vowen.modules.forms.models import BotContact

    c, app, ids, h, f = await setup_forms(api)
    await c.post(f"/api/v1/forms/{f['id']}/publish", headers=h[0], json={"expected_version": 1})
    async with app.state.sessions() as db, db.begin():
        db.add(BotContact(telegram_id=100000000002, allowed=True))
    await c.post(
        f"/api/v1/forms/{f['id']}/invitations",
        headers=h[0],
        json={
            "recipient_user_id": str(ids[1]),
            "reader_ids": [],
            "deliver": True,
        },
    )
    cipher = PayloadCipher(app.state.settings.data_keyring_file)
    async with app.state.sessions() as db, db.begin():
        task = await claim_delivery(db, NOW, cipher)
    assert task
    settings = (await c.get("/api/v1/me/notifications", headers=h[1])).json()
    body = {
        "expected_version": settings["revision"],
        "channels": ["telegram"],
        "quiet_enabled": True,
        "quiet_start": 540,
        "quiet_end": 660,
    }
    response = await c.patch("/api/v1/me/notifications", headers=h[1], json=body)
    assert response.status_code == 200
    async with app.state.sessions() as db, db.begin():
        assert not await prepare_delivery(db, task, NOW)
        await db.flush()
        assert (
            await db.execute(text("SELECT attempts FROM notification_deliveries"))
        ).scalar_one() == 0
    body.update(expected_version=response.json()["revision"], quiet_enabled=False)
    assert (await c.patch("/api/v1/me/notifications", headers=h[1], json=body)).status_code == 200
    async with app.state.sessions() as db, db.begin():
        assert await claim_delivery(db, NOW, cipher) is not None
