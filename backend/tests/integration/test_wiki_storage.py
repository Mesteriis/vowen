from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_administration import setup_members


async def test_storage_enforces_main_reference_and_revision_ownership(api):
    _, app, owner, _, _, _ = await setup_members(api)
    async with app.state.sessions.begin() as db:
        exists = await db.scalar(text("SELECT to_regclass('wiki_pages') IS NOT NULL"))
        assert exists, "Wiki storage is missing"
    from vowen.modules.wiki.models import WikiPage, WikiRevision, WikiSection

    section, first, second, revision = uuid4(), uuid4(), uuid4(), uuid4()
    async with app.state.sessions.begin() as db:
        db.add(WikiSection(uid=section, title="Root"))
        db.add_all([WikiPage(uid=first, kind="article"), WikiPage(uid=second, kind="article")])
        await db.flush()
        db.add(
            WikiRevision(
                uid=revision,
                page_uid=first,
                section_uid=section,
                title="A",
                body="Body",
                author_id=owner,
            )
        )
    async with app.state.sessions() as db:
        with pytest.raises(IntegrityError):
            await db.execute(
                text("UPDATE wiki_pages SET draft_revision_uid=:r WHERE uid=:p"),
                {"r": revision, "p": second},
            )
            await db.commit()
        await db.rollback()
        db.add(WikiPage(kind="encyclopedia"))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_main_reference_is_unique_and_cannot_be_deleted(api):
    from sqlalchemy import delete

    from vowen.modules.references.models import Device
    from vowen.modules.wiki.models import WikiPage

    _, app, _, _, _, _ = await setup_members(api)
    uid = uuid4()
    async with app.state.sessions.begin() as db:
        db.add(Device(uid=uid, name="Reference"))
        await db.flush()
        db.add(WikiPage(kind="encyclopedia", device_uid=uid))
    async with app.state.sessions() as db:
        db.add(WikiPage(kind="encyclopedia", device_uid=uid))
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()
        with pytest.raises(IntegrityError):
            await db.execute(delete(Device).where(Device.uid == uid))
            await db.commit()
        await db.rollback()
