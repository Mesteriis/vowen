import asyncio
from datetime import timedelta

from conftest import NOW
from sqlalchemy import select
from test_forms_versions import setup_forms

from vowen.core.crypto import PayloadCipher
from vowen.modules.forms.delivery import claim_delivery, complete_delivery
from vowen.modules.forms.models import BotContact, Delivery


async def test_delivery_contact_gating_claim_lease_and_secret_cleanup(api):
    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    command = {"recipient_user_id": str(ids[1]), "reader_ids": [], "deliver": True}
    first = await c.post(p + "/invitations", headers=h[0], json=command)
    assert first.status_code == 200, first.text
    assert first.json()["delivery_status"] == "manual_delivery_required"
    async with app.state.sessions() as db, db.begin():
        db.add(BotContact(telegram_id=100000000002, allowed=True))
    second = await c.post(p + "/invitations", headers=h[0], json=command)
    assert second.json()["delivery_status"] == "pending"
    crypto = PayloadCipher(app.state.settings.data_keyring_file)

    async def claim():
        async with app.state.sessions() as db, db.begin():
            return await claim_delivery(db, NOW, crypto)

    claims = await asyncio.gather(claim(), claim())
    assert sum(v is not None for v in claims) == 1
    task = next(v for v in claims if v is not None)
    assert task.telegram_id == 100000000002 and "token=" not in task.link
    async with app.state.sessions() as db:
        d = await db.scalar(select(Delivery))
        assert d.ciphertext and b"https://" in d.ciphertext
    async with app.state.sessions() as db, db.begin():
        assert await claim_delivery(db, NOW + timedelta(minutes=2), crypto) is not None
        # A late worker may not complete another worker's reclaimed lease.
        assert not await complete_delivery(db, task.id, task.lease_id, True, NOW)
    async with app.state.sessions() as db, db.begin():
        d = await db.scalar(select(Delivery))
        assert await complete_delivery(db, d.id, d.lease_id, True, NOW)
    async with app.state.sessions() as db, db.begin():
        assert await claim_delivery(db, NOW + timedelta(minutes=5), crypto) is None
        d = await db.scalar(select(Delivery))
        assert d.status == "delivered" and d.ciphertext is None and d.nonce is None


async def test_delivery_sends_neutral_text_once_and_scrubs_guest_link(api, monkeypatch):
    from vowen.modules.forms.delivery import deliver_one

    c, app, ids, h, f = await setup_forms(api)
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    async with app.state.sessions() as db, db.begin():
        db.add(BotContact(telegram_id=100000000009, allowed=True))
    issued = await c.post(
        p + "/invitations",
        headers=h[0],
        json={"reader_ids": [], "deliver": True, "contact_telegram_id": 100000000009},
    )
    assert issued.json()["delivery_status"] == "pending"
    sent = []

    async def send(chat, text):
        sent.append((chat, text))

    monkeypatch.setattr("vowen.modules.forms.delivery.Clock.now", lambda self: NOW)
    crypto = PayloadCipher(app.state.settings.data_keyring_file)
    assert await deliver_one(app.state.sessions, crypto, send)
    assert not await deliver_one(app.state.sessions, crypto, send)
    assert len(sent) == 1
    assert "Private survey" not in sent[0][1] and "Question" not in sent[0][1]
    assert "#token=" in sent[0][1]
    async with app.state.sessions() as db:
        delivery = await db.scalar(select(Delivery))
        assert delivery.ciphertext is None


async def test_submit_notification_is_atomic_neutral_and_removed_on_withdrawal(api):
    from uuid import uuid4

    c, app, ids, h, f = await setup_forms(api)
    async with app.state.sessions() as db, db.begin():
        db.add(BotContact(telegram_id=100000000003, allowed=True))
    p = "/api/v1/forms/" + f["id"]
    await c.post(p + "/publish", headers=h[0], json={"expected_version": 1})
    invitation = (
        await c.post(
            p + "/invitations",
            headers=h[0],
            json={"recipient_user_id": str(ids[1]), "reader_ids": [str(ids[2])]},
        )
    ).json()
    result = await c.post(
        "/api/v1/form-invitations/" + invitation["id"] + "/submit",
        headers=h[1],
        json={
            "answers": {"q": "Never notify this body"},
            "idempotency_key": str(uuid4()),
            "acknowledged": True,
        },
    )
    assert result.status_code == 200
    async with app.state.sessions() as db:
        delivery = await db.scalar(select(Delivery))
        assert delivery is not None
        assert delivery.kind == "response"
        crypto = PayloadCipher(app.state.settings.data_keyring_file)
        from vowen.modules.forms.service import opened

        assert "Never notify" not in str(opened(delivery, crypto))
    await c.delete("/api/v1/form-submissions/" + result.json()["id"], headers=h[1])
    async with app.state.sessions() as db:
        delivery = await db.scalar(select(Delivery))
        assert delivery.ciphertext is None and delivery.status == "cancelled"
