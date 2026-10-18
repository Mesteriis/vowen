"""Debug fixtures exercise normal APIs; unknown accounts must survive a refused reset."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from vowen.modules.identity.models import User

spec = importlib.util.spec_from_file_location(
    "seed_debug_space", Path(__file__).resolve().parents[3] / "scripts/seed_debug_space.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_reset_guard_rejects_remote_production_and_unknown_accounts():
    url = "postgresql+psycopg://local:local@127.0.0.1:55432/design_test"
    fixture.validate_reset(url, [(100000000201, "Алекс · демо")])
    for bad in [url.replace("127.0.0.1", "remote"), url.replace("design_test", "vowen")]:
        with pytest.raises(ValueError):
            fixture.validate_reset(bad, [])
    for unknown in [(999, "Real person"), (100000000201, "Real person")]:
        with pytest.raises(ValueError):
            fixture.validate_reset(url, [unknown])


async def test_three_member_debug_space_has_complete_workflows_and_isolation(api):
    _, app = api
    # The local day is already tomorrow in Madrid: exercise the midnight boundary.
    app.state.clock = type(
        "LateClock", (), {"now": lambda self: datetime(2026, 10, 18, 23, 30, tzinfo=UTC)}
    )()
    app.state.settings.app_env = "development"
    app.state.settings.debug_auth = True
    app.state.settings.public_base_url = "http://127.0.0.1:5176"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:5176",
        headers={"Origin": "http://127.0.0.1:5176"},
    ) as client:
        result = await fixture.populate(app, client)
        assert set(result["participants"]) == {"alex", "vika", "luna"}
        assert len(result["relations"]) == 2
        assert result["products"] == 103
        for key in ["vika", "luna"]:
            assert result["wallets"][key]["reserved"] == 120
            assert result["wallets"][key]["balance"] == (1240 if key == "vika" else 940)
        assert result["checks"]["profiles_completed"] == 3
        assert result["checks"]["questionnaires_submitted"] == 3
        assert result["checks"]["transitive_access_denied"]
        assert result["checks"]["private_journals"] == 3
    async with app.state.sessions() as db:
        users = list(await db.scalars(select(User).order_by(User.telegram_id)))
        assert [(u.display_name, u.shop_role, u.is_admin) for u in users] == [
            ("Алекс", "dominant", True),
            ("Вика", "switch", False),
            ("Луна", "bottom", False),
        ]


async def test_populate_refuses_normal_app_without_creating_accounts(api):
    client, app = api
    with pytest.raises(ValueError, match="development debug"):
        await fixture.populate(app, client)
    async with app.state.sessions() as db:
        assert await db.scalar(select(User.id).limit(1)) is None


def test_failed_backup_removes_partial_private_dump(tmp_path, monkeypatch):
    def fail_dump(*args, **kwargs):
        output = next(tmp_path.glob("*.dump"))
        assert output.stat().st_mode & 0o777 == 0o600
        raise OSError("Unavailable local pg_dump")

    monkeypatch.setattr(fixture.subprocess, "run", fail_dump)
    with pytest.raises(RuntimeError, match="reset was not started"):
        fixture.backup_database(
            "postgresql+psycopg://local:local@127.0.0.1:55432/design_test", tmp_path
        )
    assert not list(tmp_path.glob("*.dump"))
