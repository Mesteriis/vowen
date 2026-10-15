"""Rehearse M5 upgrade/downgrade on synthetic existing M4 rows only."""

import asyncio
import os

from sqlalchemy import text
from test_forms_versions import setup_forms
from test_journal_privacy import create


async def test_m5_migration_preserves_existing_profile_and_encrypted_journal(api):
    client, app, _, headers, form = await setup_forms(api)
    # setup_forms creates a real authenticated synthetic profile and draft form.
    token = headers[0]["Authorization"].removeprefix("Bearer ")
    entry = await create(client, {"access_token": token})
    async with app.state.engine.connect() as conn:
        before = (
            await conn.execute(
                text(
                    "SELECT user_id,language,timezone,profile_labels,profile_version "
                    "FROM user_preferences ORDER BY user_id"
                )
            )
        ).all()
        journal = (await conn.execute(text("SELECT * FROM journal_entries"))).all()
        forms = (await conn.execute(text("SELECT * FROM forms"))).all()
    url = app.state.settings.database_url
    assert url.rsplit("/", 1)[-1].endswith("_test")

    async def migration(command, revision):
        process = await asyncio.create_subprocess_exec(
            "alembic",
            "-c",
            "backend/alembic.ini",
            command,
            revision,
            env={**os.environ, "DATABASE_URL": url},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        assert process.returncode == 0, (stdout + stderr).decode()

    try:
        await migration("downgrade", "0016")
        await migration("upgrade", "head")
        async with app.state.engine.connect() as conn:
            assert (
                await conn.execute(
                    text(
                        "SELECT user_id,language,timezone,profile_labels,profile_version "
                        "FROM user_preferences ORDER BY user_id"
                    )
                )
            ).all() == before
            assert (await conn.execute(text("SELECT * FROM journal_entries"))).all() == journal
            assert (await conn.execute(text("SELECT * FROM forms"))).all() == forms
            assert (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM user_preferences WHERE notification_channels="
                        '\'["in_app","telegram"]\'::jsonb AND NOT quiet_enabled '
                        "AND notification_revision=1"
                    )
                )
            ).scalar_one() == len(before)
        assert (await client.get(f"/api/v1/journal/{entry['id']}", headers=headers[0])).json()[
            "text"
        ] == "private-journal-body"
        assert (await client.get("/api/v1/forms", headers=headers[0])).json()[0]["id"] == form["id"]
    finally:
        await migration("upgrade", "head")
