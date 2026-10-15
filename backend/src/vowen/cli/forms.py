import asyncio
from uuid import UUID

import typer

from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.crypto import PayloadCipher
from vowen.core.database import engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.forms.models import Form
from vowen.modules.forms.schemas import InvitationCreate
from vowen.modules.forms.service import invite

forms_app = typer.Typer(help="Operator form invitations; never consent or answer for a member.")


@forms_app.command("invite")
def invitation(
    form_id: UUID,
    reader_id: list[UUID] = typer.Option([]),
    recipient_id: UUID | None = None,
    ttl_days: int = 7,
    retention_days: int = 90,
    deliver: bool = False,
    contact_telegram_id: int | None = None,
) -> None:
    """Issue an invitation for an already published form. Guest links are secrets."""

    async def execute() -> tuple[str, str]:
        settings = Settings()
        engine = engine_for(settings.database_url)
        try:
            async with sessions_for(engine)() as db, db.begin():
                f = await db.get(Form, form_id)
                if f is None:
                    raise AppError(404, "NOT_FOUND")
                result = await invite(
                    db,
                    f.author_id,
                    f.id,
                    InvitationCreate(
                        recipient_user_id=recipient_id,
                        reader_ids=reader_id,
                        ttl_days=ttl_days,
                        retention_days=retention_days,
                        deliver=deliver,
                        contact_telegram_id=contact_telegram_id,
                    ),
                    Clock().now(),
                    settings.public_base_url,
                    PayloadCipher(settings.data_keyring_file),
                )
                return result.link or "", result.delivery_status
        finally:
            await engine.dispose()

    try:
        link, status = asyncio.run(execute())
    except (AppError, ValueError, OSError):
        typer.echo("Invitation unavailable", err=True)
        raise typer.Exit(1) from None
    typer.echo(link)
    typer.echo(status, err=True)
