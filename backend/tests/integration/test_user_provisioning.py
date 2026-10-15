import pytest
from conftest import NOW
from sqlalchemy import func, select

from vowen.core.errors import AppError
from vowen.modules.identity.models import User
from vowen.modules.identity.service import ProvisionUserCommand, create_user, set_user_active


async def test_bigint_duplicate_and_disable(api):
    _, app = api
    async with app.state.sessions() as db:
        user = await create_user(
            db, ProvisionUserCommand(telegram_id=100000000001, display_name="Demo D1"), NOW
        )
        await db.commit()
        assert user.telegram_id == 100000000001
        with pytest.raises(AppError):
            await create_user(
                db, ProvisionUserCommand(telegram_id=100000000001, display_name="Other"), NOW
            )
        await db.rollback()
        await set_user_active(db, 100000000001, False, NOW)
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(User)) == 1
        assert not (await db.scalar(select(User))).is_active


async def test_no_registration_endpoint(api):
    client, _ = api
    for path in ("/register", "/signup", "/users"):
        assert (await client.post("/api/v1" + path, json={})).status_code == 404
