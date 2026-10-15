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
    original = (tmp_path / "keyring.json").read_bytes()
    assert runner.invoke(app, ["instance", "init"]).exit_code == 0
    assert (tmp_path / "keyring.json").read_bytes() == original
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
