from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from test_sessions import provision


async def test_profile_reference_integrity(api):
    from vowen.modules.identity.models import User
    from vowen.modules.participant_profiles.models import PracticePreference, Profile
    from vowen.modules.references.models import Practice

    _, app = api
    owner = await provision(app)
    practice = uuid4()
    async with app.state.sessions.begin() as db:
        db.add(Profile(user_id=owner))
        db.add(Practice(uid=practice, name="A practice"))
    async with app.state.sessions.begin() as db:
        db.add(PracticePreference(owner_id=owner, practice_uid=practice))
    async with app.state.sessions() as db:
        with pytest.raises(IntegrityError):
            async with db.begin():
                db.add(PracticePreference(owner_id=owner, practice_uid=uuid4()))
                await db.flush()
    async with app.state.sessions() as db:
        with pytest.raises(IntegrityError):
            async with db.begin():
                db.add(PracticePreference(owner_id=owner, practice_uid=practice))
                await db.flush()
    async with app.state.sessions.begin() as db:
        # Existing account has other records with restrictive FKs; test owned profile deletion.
        await db.execute(delete(Profile).where(Profile.user_id == owner))
    async with app.state.sessions() as db:
        assert (
            await db.scalar(select(PracticePreference).where(PracticePreference.owner_id == owner))
            is None
        )
        assert await db.get(User, owner) is not None
