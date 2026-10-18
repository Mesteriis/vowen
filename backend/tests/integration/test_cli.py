from typer.testing import CliRunner

from vowen.cli.main import app


def test_cli_provision_duplicate_disable_and_init(tmp_path, monkeypatch):
    import os

    test_url = os.environ.get(
        "TEST_DATABASE_URL", "postgresql+psycopg://vowen:vowen@127.0.0.1:55432/vowen_test"
    )
    if not test_url.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError("Dedicated test database required")
    monkeypatch.setenv("DATABASE_URL", test_url)
    monkeypatch.setenv("DATA_KEYRING_FILE", str(tmp_path / "keyring.json"))
    runner = CliRunner()
    assert runner.invoke(app, ["instance", "init"]).exit_code == 0
    assert not (tmp_path / "keyring.json").exists()
    assert runner.invoke(app, ["instance", "init"]).exit_code == 0
    assert not (tmp_path / "keyring.json").exists()
    import asyncio

    from sqlalchemy import text

    from vowen.core.database import engine_for

    async def clean():
        engine = engine_for(test_url)
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE users CASCADE"))
        await engine.dispose()

    asyncio.run(clean())
    args = ["users", "create", "--telegram-id", "100000000099", "--display-name", "CLI demo"]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code != 0
    assert runner.invoke(app, ["users", "disable", "--telegram-id", "100000000099"]).exit_code == 0
    assert runner.invoke(app, ["users", "enable", "--telegram-id", "100000000099"]).exit_code == 0
    assert (
        runner.invoke(app, ["users", "revoke-sessions", "--telegram-id", "100000000099"]).exit_code
        == 0
    )


def test_cli_relation_is_only_a_proposal(tmp_path, monkeypatch):
    import asyncio
    import os
    from uuid import UUID

    from sqlalchemy import func, select, text

    from vowen.core.clock import Clock
    from vowen.core.database import engine_for, sessions_for
    from vowen.modules.identity.service import ProvisionUserCommand, create_user
    from vowen.modules.relations.models import Consent, Relation

    url = os.environ.get(
        "TEST_DATABASE_URL", "postgresql+psycopg://vowen:vowen@127.0.0.1:55432/vowen_test"
    )
    assert url.rsplit("/", 1)[-1].endswith("_test")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATA_KEYRING_FILE", str(tmp_path / "keyring.json"))
    runner = CliRunner()
    assert runner.invoke(app, ["instance", "init"]).exit_code == 0
    agreement = tmp_path / "agreement.txt"
    agreement.write_text("synthetic CLI agreement")

    async def seed():
        engine = engine_for(url)
        async with sessions_for(engine)() as db, db.begin():
            await db.execute(text("TRUNCATE users CASCADE"))
            ids = []
            for index in range(2):
                ids.append(
                    (
                        await create_user(
                            db,
                            ProvisionUserCommand(
                                telegram_id=100000000301 + index, display_name="CLI demo"
                            ),
                            Clock().now(),
                        )
                    ).id
                )
        await engine.dispose()
        return ids

    a, b = asyncio.run(seed())
    command = [
        "relations",
        "propose",
        "--dominant-id",
        str(a),
        "--submissive-id",
        str(b),
        "--scope",
        "rules.assign",
        "--agreement-file",
        str(agreement),
    ]
    result = runner.invoke(app, command)
    assert result.exit_code == 0, result.output
    relation_id = UUID(result.output.strip())
    assert "synthetic CLI agreement" not in result.output
    assert runner.invoke(app, command).exit_code == 1
    assert runner.invoke(app, ["relations", "accept", str(relation_id)]).exit_code != 0
    assert runner.invoke(app, [*command[:-1], str(tmp_path / "missing.txt")]).exit_code != 0
    invalid = command.copy()
    invalid[invalid.index("rules.assign")] = "journal.read"
    assert runner.invoke(app, invalid).exit_code != 0

    async def check():
        engine = engine_for(url)
        async with sessions_for(engine)() as db:
            relation = await db.get(Relation, relation_id)
            assert relation.status == "proposed"
            assert await db.scalar(select(func.count()).select_from(Consent)) == 0
        await engine.dispose()

    asyncio.run(check())
