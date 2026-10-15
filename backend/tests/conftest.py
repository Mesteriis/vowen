import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

from vowen.core.config import Settings
from vowen.main import create_app

NOW = datetime(2026, 10, 15, 10, tzinfo=UTC)
BOT_TOKEN = "123456:synthetic_test_token_not_a_real_credential"


@pytest.fixture
async def api(tmp_path: Path):
    token_file = tmp_path / "bot-token"
    token_file.write_text(BOT_TOKEN)
    settings = Settings(
        database_url=os.environ.get(
            "TEST_DATABASE_URL", "postgresql+psycopg://vowen:vowen@127.0.0.1:55432/vowen_test"
        ),
        telegram_bot_token_file=token_file,
        data_keyring_file=tmp_path / "keyring.json",
    )
    if not settings.database_url.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError("Tests require a dedicated database ending in _test")
    app = create_app(settings)
    app.state.clock = type("FixedClock", (), {"now": lambda self: NOW})()
    async with app.state.engine.begin() as conn:
        tables = (
            (
                await conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                        "AND tablename NOT IN ('alembic_version','instance_settings')"
                    )
                )
            )
            .scalars()
            .all()
        )
        if tables:
            await conn.execute(
                text("TRUNCATE " + ",".join('"' + t + '"' for t in tables) + " CASCADE")
            )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        yield client, app
    await app.state.engine.dispose()
