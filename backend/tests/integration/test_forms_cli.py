import asyncio
from uuid import UUID

from sqlalchemy import func, select
from test_forms_versions import setup_forms
from typer.testing import CliRunner

from vowen.cli.main import app as cli
from vowen.modules.forms.models import Invitation, Submission
from vowen.modules.identity.models import User


async def test_operator_cli_issues_capability_but_never_answers_or_creates_user(api, monkeypatch):
    c, app, ids, h, f = await setup_forms(api)
    await c.post(
        "/api/v1/forms/" + f["id"] + "/publish", headers=h[0], json={"expected_version": 1}
    )
    monkeypatch.setenv("DATABASE_URL", app.state.settings.database_url)
    monkeypatch.setenv("DATA_KEYRING_FILE", str(app.state.settings.data_keyring_file))
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://test")
    result = await asyncio.to_thread(
        CliRunner().invoke,
        cli,
        ["forms", "invite", f["id"], "--reader-id", str(ids[2]), "--deliver"],
    )
    assert result.exit_code == 0
    link = result.stdout.strip()
    assert "manual_delivery_required" in result.stderr
    assert link.startswith("https://test/f/") and "#token=" in link
    iid = UUID(link.split("/f/")[1].split("#")[0])
    async with app.state.sessions() as db:
        i = await db.get(Invitation, iid)
        assert i.activated_at is None and i.recipient_user_id is None
        response = await db.scalar(select(Submission).where(Submission.invitation_id == iid))
        assert response.status == "draft" and response.ciphertext is None
        assert await db.scalar(select(func.count()).select_from(User)) == 3
