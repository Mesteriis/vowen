import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from conftest import NOW
from sqlalchemy import text
from test_rewards import reward_setup
from test_ritual_review import setup_ritual
from test_sessions import auth


async def opt_in(app):
    async with app.state.sessions() as db, db.begin():
        await db.execute(
            text("INSERT INTO bot_contacts(telegram_id,allowed) SELECT telegram_id,true FROM users")
        )


async def enqueue_assignment(api):
    client, app, ids, tokens, ritual, a, o = await setup_ritual(api)
    await opt_in(app)
    command = {
        "recipient_id": str(ids[1]),
        "reviewer_ids": [str(ids[0]), str(ids[2])],
        "approval_required": True,
        "idempotency_key": str(uuid4()),
        "schedule": a["schedule"],
    }
    result = await client.post(
        f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(tokens[0]), json=command
    )
    assert result.status_code == 200
    repeated = await client.post(
        f"/api/v1/rituals/{ritual['id']}/assignments", headers=auth(tokens[0]), json=command
    )
    assert repeated.json()["id"] == result.json()["id"]
    return client, app, ids, tokens, result.json()


async def test_atomic_enqueue_opt_in_no_backfill_and_duplicate_event(api):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    async with app.state.sessions() as db:
        states = (
            await db.execute(text("SELECT status,count(*) FROM member_deliveries GROUP BY status"))
        ).all()
        assert dict(states) == {"suppressed": 2, "pending": 2}  # assigned + due per assignment
    from vowen.modules.notifications.delivery import claim, complete, prepare

    sent = []
    for _ in range(5):
        async with app.state.sessions() as db, db.begin():
            task = await claim(db, NOW)
        if task:
            async with app.state.sessions() as db, db.begin():
                ready = await prepare(db, task, NOW)
            assert ready is not None
            sent.append(ready.telegram_id)
            async with app.state.sessions() as db, db.begin():
                assert await complete(db, task, "delivered", NOW)
                assert not await complete(db, task, "delivered", NOW)
    assert sent == [100000000002, 100000000002]


@pytest.mark.parametrize("deny", ["contact", "pause", "disable", "relation", "assignment", "age"])
async def test_revocation_after_claim_prevents_send(api, deny):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    from vowen.modules.notifications.delivery import claim, prepare

    async with app.state.sessions() as db, db.begin():
        task = await claim(db, NOW)
    assert task is not None
    async with app.state.sessions() as db, db.begin():
        statements = {
            "contact": "UPDATE bot_contacts SET allowed=false",
            "pause": "UPDATE users SET paused=true",
            "disable": "UPDATE users SET is_active=false",
            "relation": "UPDATE authority_relations SET status='revoked'",
            "assignment": "UPDATE ritual_assignments SET status='revoked'",
            "age": "UPDATE member_deliveries SET created_at=created_at-interval '2 days'",
        }
        await db.execute(text(statements[deny]))
    async with app.state.sessions() as db, db.begin():
        assert await prepare(db, task, NOW) is None
        await db.flush()
        assert (
            await db.execute(
                text("SELECT status FROM member_deliveries WHERE id=:id"), {"id": task.id}
            )
        ).scalar() == "suppressed"


async def test_concurrent_claims_lease_fencing_and_uncertain_crash(api):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    from vowen.modules.notifications.delivery import claim, complete, prepare

    async def get_one():
        async with app.state.sessions() as db, db.begin():
            return await claim(db, NOW)

    first, second = await asyncio.gather(get_one(), get_one())
    assert first and second and first.id != second.id
    async with app.state.sessions() as db, db.begin():
        replacement = await claim(db, NOW + timedelta(minutes=2))
    assert replacement and replacement.id in {first.id, second.id}
    old = first if first.id == replacement.id else second
    async with app.state.sessions() as db, db.begin():
        assert await prepare(db, old, NOW + timedelta(minutes=2)) is None
        assert await prepare(db, replacement, NOW + timedelta(minutes=2)) is not None
    async with app.state.sessions() as db, db.begin():
        await claim(db, NOW + timedelta(minutes=4))
        await db.flush()
        assert (
            await db.execute(
                text("SELECT status FROM member_deliveries WHERE id=:id"), {"id": replacement.id}
            )
        ).scalar() == "uncertain"
        assert not await complete(db, replacement, "delivered", NOW + timedelta(minutes=4))


async def test_reward_enqueue_retry_and_withdrawal_preserves_history(api):
    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    await opt_in(app)
    command = {
        "reward_version_id": reward["version_id"],
        "recipient_id": str(ids[1]),
        "idempotency_key": str(uuid4()),
    }
    results = await asyncio.gather(
        *(
            client.post("/api/v1/reward-grants", headers=auth(tokens[0]), json=command)
            for _ in range(2)
        )
    )
    assert results[0].json()["id"] == results[1].json()["id"]
    from vowen.modules.notifications.delivery import claim, prepare

    async with app.state.sessions() as db, db.begin():
        assert (
            await db.scalar(
                text("SELECT count(*) FROM member_deliveries WHERE reward_notice_id IS NOT NULL")
            )
            == 2
        )
        task = await claim(db, NOW)
        assert task
        await db.execute(text("UPDATE authority_relations SET status='revoked'"))
    async with app.state.sessions() as db, db.begin():
        assert await prepare(db, task, NOW) is None
    assert len((await client.get("/api/v1/reward-grants", headers=auth(tokens[1]))).json()) == 1


async def only_one_pending(app):
    async with app.state.sessions() as db, db.begin():
        did = await db.scalar(
            text("SELECT id FROM member_deliveries WHERE status='pending' ORDER BY id LIMIT 1")
        )
        await db.execute(
            text("UPDATE member_deliveries SET status='suppressed' WHERE id<>:id"), {"id": did}
        )
        return did


@pytest.mark.parametrize("outcome", ["success", "blocked", "timeout", "retry"])
async def test_delivery_outcomes_no_transaction_and_no_ambiguous_repeat(api, monkeypatch, outcome):
    from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
    from aiogram.methods import SendMessage

    from vowen.modules.notifications import delivery

    client, app, ids, tokens, a = await enqueue_assignment(api)
    did = await only_one_pending(app)
    now = NOW
    monkeypatch.setattr(delivery.Clock, "now", lambda self: now)
    sent = []

    async def send(chat, body):
        # A second transaction can lock the row while network IO is in progress.
        async with app.state.sessions() as db, db.begin():
            await db.execute(text("SET LOCAL lock_timeout='250ms'"))
            state = await db.scalar(
                text("SELECT status FROM member_deliveries WHERE id=:id FOR UPDATE"), {"id": did}
            )
            assert state == "sending"
        sent.append((chat, body))
        if outcome == "blocked":
            raise TelegramForbiddenError(
                SendMessage(chat_id=chat, text=body), "synthetic forbidden"
            )
        if outcome == "timeout":
            raise TimeoutError("synthetic token must never be logged")
        if outcome == "retry":
            raise TelegramRetryAfter(
                SendMessage(chat_id=chat, text=body), "synthetic flood", retry_after=90
            )

    assert await delivery.deliver_one(app.state.sessions, "https://test", send)
    assert not await delivery.deliver_one(app.state.sessions, "https://test", send)
    assert sent[0][0] == 100000000002
    assert "Morning" not in sent[0][1] and "Private" not in sent[0][1]
    assert "https://test" in sent[0][1] and "token" not in sent[0][1]
    if outcome == "retry":
        now += timedelta(seconds=89)
        assert not await delivery.deliver_one(app.state.sessions, "https://test", send)
        now += timedelta(seconds=1)
        assert await delivery.deliver_one(app.state.sessions, "https://test", send)
        now += timedelta(seconds=90)
        assert await delivery.deliver_one(app.state.sessions, "https://test", send)
        now += timedelta(seconds=90)
        assert not await delivery.deliver_one(app.state.sessions, "https://test", send)
        assert len(sent) == 3
    else:
        now += timedelta(minutes=2)
        assert not await delivery.deliver_one(app.state.sessions, "https://test", send)
        assert len(sent) == 1
    async with app.state.sessions() as db:
        state = await db.scalar(
            text("SELECT status FROM member_deliveries WHERE id=:id"), {"id": did}
        )
        assert (
            state
            == {
                "success": "delivered",
                "timeout": "uncertain",
                "retry": "manual_delivery_required",
                "blocked": "manual_delivery_required",
            }[outcome]
        )
        if outcome == "blocked":
            assert (
                await db.scalar(
                    text("SELECT allowed FROM bot_contacts WHERE telegram_id=100000000002")
                )
                is False
            )


async def test_rollback_removes_both_notice_and_delivery(api):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    from vowen.modules.rituals.models import RitualAssignment
    from vowen.modules.rituals.service import notice

    async with app.state.sessions() as db:
        before = await db.scalar(text("SELECT count(*) FROM member_deliveries"))
        row = await db.get(RitualAssignment, UUID(a["id"]))
        await notice(db, row, [ids[1]], "assigned", NOW, event="rollback-event")
        await db.flush()
        assert await db.scalar(text("SELECT count(*) FROM member_deliveries")) == before + 1
        await db.rollback()
    async with app.state.sessions() as db:
        assert await db.scalar(text("SELECT count(*) FROM member_deliveries")) == before
        assert (
            await db.scalar(
                text("SELECT count(*) FROM ritual_notices WHERE event_key='rollback-event'")
            )
            == 0
        )


@pytest.mark.parametrize("forms_failure", [False, True])
async def test_bot_tick_routes_member_queue_localizes_and_disables_previews(
    api, monkeypatch, forms_failure
):
    from aiogram import Bot
    from aiogram.methods import SendMessage
    from conftest import BOT_TOKEN
    from test_bot_adapter import TelegramTransport

    from vowen.integrations.telegram import bot as adapter

    client, app, ids, tokens, a = await enqueue_assignment(api)
    await only_one_pending(app)
    async with app.state.sessions() as db, db.begin():
        await db.execute(
            text("UPDATE user_preferences SET language='ru' WHERE user_id=:id"), {"id": ids[1]}
        )
    monkeypatch.setattr("vowen.modules.notifications.delivery.Clock.now", lambda self: NOW)
    methods = []

    class Transport(TelegramTransport):
        async def make_request(self, bot, method, timeout=None):
            methods.append((method, timeout))
            return await super().make_request(bot, method, timeout)

    if forms_failure:

        async def fail(*args):
            raise RuntimeError("synthetic secret must not enter logs")

        monkeypatch.setattr(adapter, "deliver_one", fail)
    bot = Bot(BOT_TOKEN, session=Transport())
    await adapter.deliver_updates(
        app.state.sessions, app.state.settings.data_keyring_file, bot, "https://test"
    )
    assert len(methods) == 1
    method, timeout = methods[0]
    assert isinstance(method, SendMessage) and method.chat_id == 100000000002
    assert method.text == "У вас есть обновление в приложении\nhttps://test/"
    assert method.parse_mode is None
    assert method.link_preview_options.is_disabled is True
    assert timeout == 30
    await bot.session.close()


async def test_pause_resume_without_worker_does_not_resurrect_queued_notices(api):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    from vowen.modules.notifications.delivery import claim, prepare

    async with app.state.sessions() as db, db.begin():
        task = await claim(db, NOW)
    assert task
    assert (await client.post("/api/v1/me/pause", headers=auth(tokens[1]))).status_code == 204
    assert (await client.post("/api/v1/me/resume", headers=auth(tokens[1]))).status_code == 204
    async with app.state.sessions() as db, db.begin():
        assert await prepare(db, task, NOW) is None
        assert await claim(db, NOW) is None


async def test_bot_opt_out_then_in_does_not_resurrect_queued_delivery(api):
    from aiogram import Bot, Dispatcher
    from aiogram.types import Chat, Message, Update, User
    from conftest import BOT_TOKEN
    from test_bot_adapter import TelegramTransport

    from vowen.integrations.telegram.bot import build_router
    from vowen.modules.notifications.delivery import claim, prepare

    client, app, ids, tokens, a = await enqueue_assignment(api)
    async with app.state.sessions() as db, db.begin():
        task = await claim(db, NOW)
    assert task
    bot = Bot(BOT_TOKEN, session=TelegramTransport())
    dispatcher = Dispatcher()
    router = build_router(app.state.settings)
    dispatcher.include_router(router)
    for i, command in enumerate(["/notifications_off", "/notifications_on"]):
        await dispatcher.feed_update(
            bot,
            Update(
                update_id=i + 1,
                message=Message(
                    message_id=i + 1,
                    date=NOW,
                    chat=Chat(id=100000000002, type="private"),
                    from_user=User(id=100000000002, is_bot=False, first_name="Synthetic"),
                    text=command,
                    entities=[{"type": "bot_command", "offset": 0, "length": len(command)}],
                ),
            ),
        )
    async with app.state.sessions() as db, db.begin():
        assert await prepare(db, task, NOW) is None
        assert await claim(db, NOW) is None
    await router.emit_shutdown()
    await bot.session.close()


async def test_stale_occurrence_and_removed_reviewer_never_notify(api):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    occurrences = (await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))).json()
    o = next(item for item in occurrences if item["assignment_id"] == a["id"])
    submitted = await client.post(
        f"/api/v1/ritual-occurrences/{o['id']}/report",
        headers=auth(tokens[1]),
        json={
            "expected_version": o["revision"],
            "idempotency_key": str(uuid4()),
            "text": "Never leak this report",
        },
    )
    assert submitted.status_code == 200
    from vowen.modules.notifications.delivery import claim

    async with app.state.sessions() as db, db.begin():
        # Keep the old due notice and the current reviewer2 notice; discard unrelated test events.
        await db.execute(
            text("""UPDATE member_deliveries d SET status='suppressed'
            FROM ritual_notices n WHERE d.ritual_notice_id=n.id AND NOT
            (n.assignment_id=:aid AND
            (n.kind='due' OR (n.kind='submitted' AND n.user_id=:uid)))"""),
            {"aid": UUID(a["id"]), "uid": ids[2]},
        )
        await db.execute(
            text("UPDATE authority_relations SET status='revoked' WHERE dominant_user_id=:uid"),
            {"uid": ids[2]},
        )
        assert await claim(db, NOW) is None
    # The unrelated active reviewer retains access to the report.
    assert (
        len((await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[0]))).json()) == 2
    )


async def test_reward_transition_suppresses_old_revision_not_new_event(api):
    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    await opt_in(app)
    grant = (
        await client.post(
            "/api/v1/reward-grants",
            headers=auth(tokens[0]),
            json={
                "reward_version_id": reward["version_id"],
                "recipient_id": str(ids[1]),
                "idempotency_key": str(uuid4()),
            },
        )
    ).json()
    assert (
        await client.post(
            f"/api/v1/reward-grants/{grant['id']}/transitions",
            headers=auth(tokens[1]),
            json={"expected_version": 1, "action": "accept"},
        )
    ).status_code == 200
    from vowen.modules.notifications.delivery import claim, complete, prepare

    sent = []
    for _ in range(3):
        async with app.state.sessions() as db, db.begin():
            task = await claim(db, NOW)
        if task:
            async with app.state.sessions() as db, db.begin():
                dest = await prepare(db, task, NOW)
                sent.append(dest.telegram_id)
            async with app.state.sessions() as db, db.begin():
                await complete(db, task, "delivered", NOW)
    assert sorted(sent) == [100000000001, 100000000002]
    async with app.state.sessions() as db:
        assert (
            await db.scalar(
                text(
                    "SELECT count(*) FROM member_deliveries WHERE reward_notice_id IS NOT NULL "
                    "AND status='suppressed'"
                )
            )
            == 2
        )


async def change_bot_preference(app, enabled):
    from aiogram import Bot, Dispatcher
    from aiogram.types import Chat, Message, Update, User
    from conftest import BOT_TOKEN
    from test_bot_adapter import TelegramTransport

    from vowen.integrations.telegram.bot import build_router

    bot = Bot(BOT_TOKEN, session=TelegramTransport())
    dispatcher = Dispatcher()
    router = build_router(app.state.settings)
    dispatcher.include_router(router)
    command = "/notifications_on" if enabled else "/notifications_off"
    await dispatcher.feed_update(
        bot,
        Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=NOW,
                chat=Chat(id=100000000002, type="private"),
                from_user=User(id=100000000002, is_bot=False, first_name="Synthetic"),
                text=command,
                entities=[{"type": "bot_command", "offset": 0, "length": len(command)}],
            ),
        ),
    )
    await router.emit_shutdown()
    await bot.session.close()


async def test_concurrent_uncommitted_enqueue_cannot_escape_opt_out(api):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    from vowen.modules.notifications.delivery import claim
    from vowen.modules.rituals.models import RitualAssignment
    from vowen.modules.rituals.service import notice

    async with app.state.sessions() as db, db.begin():
        row = await db.get(RitualAssignment, UUID(a["id"]))
        await notice(db, row, [ids[1]], "assigned", NOW, event="concurrent-denial")
        await db.flush()  # invisible to opt-out transaction until this transaction commits
        await change_bot_preference(app, False)
    await change_bot_preference(app, True)
    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None


@pytest.mark.parametrize("denial", ["contact", "pause"])
async def test_denial_while_sending_429_never_retries_after_restore(api, denial):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    from vowen.modules.notifications.delivery import claim, complete, prepare

    async with app.state.sessions() as db, db.begin():
        task = await claim(db, NOW)
        assert task
        assert await prepare(db, task, NOW)
    if denial == "contact":
        await change_bot_preference(app, False)
        await change_bot_preference(app, True)
    else:
        await client.post("/api/v1/me/pause", headers=auth(tokens[1]))
        await client.post("/api/v1/me/resume", headers=auth(tokens[1]))
    async with app.state.sessions() as db, db.begin():
        assert await complete(db, task, "retry", NOW, 90)
    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW + timedelta(seconds=91)) is None


@pytest.mark.parametrize("submitted", [False, True])
async def test_assignment_pause_resume_cancels_assigned_and_reviewer_notices(api, submitted):
    client, app, ids, tokens, a = await enqueue_assignment(api)
    if submitted:
        occurrences = (
            await client.get("/api/v1/ritual-occurrences", headers=auth(tokens[1]))
        ).json()
        o = next(item for item in occurrences if item["assignment_id"] == a["id"])
        assert (
            await client.post(
                f"/api/v1/ritual-occurrences/{o['id']}/report",
                headers=auth(tokens[1]),
                json={
                    "expected_version": o["revision"],
                    "idempotency_key": str(uuid4()),
                    "text": "private proof",
                },
            )
        ).status_code == 200
    async with app.state.sessions() as db, db.begin():
        await db.execute(
            text(
                "UPDATE member_deliveries SET status='suppressed' WHERE ritual_notice_id NOT IN "
                "(SELECT id FROM ritual_notices WHERE assignment_id=:id)"
            ),
            {"id": UUID(a["id"])},
        )
    proposal = await client.post(
        "/api/v1/change-requests",
        headers=auth(tokens[1]),
        json={
            "kind": "ritual_pause",
            "assignment_id": a["id"],
            "expected_version": a["revision"],
            "idempotency_key": str(uuid4()),
            "reason": "Synthetic planned pause",
        },
    )
    assert proposal.status_code == 200
    q = proposal.json()
    assert (
        await client.post(
            f"/api/v1/change-requests/{q['id']}/approve",
            headers=auth(tokens[0]),
            json={"expected_version": q["revision"]},
        )
    ).status_code == 200
    a = next(
        item
        for item in (await client.get("/api/v1/ritual-assignments", headers=auth(tokens[0]))).json()
        if item["id"] == a["id"]
    )
    result = await client.post(
        f"/api/v1/ritual-assignments/{a['id']}/resume",
        headers=auth(tokens[0]),
        json={"expected_version": a["revision"]},
    )
    assert result.status_code == 200
    from vowen.modules.notifications.delivery import claim

    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None


async def test_form_delivery_requires_no_keyring(api, tmp_path, monkeypatch):
    from aiogram import Bot
    from conftest import BOT_TOKEN
    from test_bot_adapter import TelegramTransport
    from test_forms_versions import setup_forms

    from vowen.integrations.telegram.bot import deliver_updates

    c, app, ids, h, f = await setup_forms(api)
    await opt_in(app)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    issued = await c.post(
        p + "/invitations",
        headers=h[0],
        json={"recipient_user_id": str(ids[1]), "reader_ids": [], "deliver": True},
    )
    assert issued.json()["delivery_status"] == "pending"
    monkeypatch.setattr("vowen.modules.forms.delivery.Clock.now", lambda self: NOW)
    bot = Bot(BOT_TOKEN, session=TelegramTransport())
    path = tmp_path / "temporarily-missing-keyring.json"
    await deliver_updates(app.state.sessions, path, bot, "https://test")
    assert not path.exists()
    async with app.state.sessions() as db:
        assert await db.scalar(text("SELECT status FROM notification_deliveries")) == "delivered"
    await bot.session.close()


async def test_uncommitted_reward_event_cannot_escape_relation_pause_interval(api):
    from test_relations import accept

    from vowen.modules.notifications.delivery import claim
    from vowen.modules.rewards.models import RewardGrant
    from vowen.modules.rewards.service import record

    client, app, ids, tokens, ritual, reward = await reward_setup(api)
    await opt_in(app)
    grant = (
        await client.post(
            "/api/v1/reward-grants",
            headers=auth(tokens[0]),
            json={
                "reward_version_id": reward["version_id"],
                "recipient_id": str(ids[1]),
                "idempotency_key": str(uuid4()),
            },
        )
    ).json()
    relation = (await client.get("/api/v1/relations", headers=auth(tokens[0]))).json()[0]
    async with app.state.sessions() as db, db.begin():
        g = await db.get(RewardGrant, UUID(grant["id"]), with_for_update=True)
        g.revision = 2
        g.status = "accepted"
        await record(db, g, ids[1], NOW)
        await db.flush()
        for action in ("pause", "resume"):
            response = await asyncio.wait_for(
                client.post(
                    f"/api/v1/relations/{relation['id']}/{action}",
                    headers=auth(tokens[0]),
                    json={"expected_version": relation["version"]},
                ),
                5,
            )
            assert response.status_code == 200
            relation = response.json()
        relation = (await accept(client, tokens[0], relation)).json()
        assert (await accept(client, tokens[1], relation)).status_code == 200
    async with app.state.sessions() as db, db.begin():
        assert await claim(db, NOW) is None
