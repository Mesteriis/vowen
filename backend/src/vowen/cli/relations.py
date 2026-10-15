from pathlib import Path
from uuid import UUID

import typer
from pydantic import ValidationError

from vowen.core.config import Settings
from vowen.core.crypto import PayloadCipher
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.auth.service import OperatorContext
from vowen.modules.relations.schemas import ProposeRelationCommand
from vowen.modules.relations.service import propose_relation

relations = typer.Typer(help="Propose relations; only participants can consent.")


async def execute_proposal(command: ProposeRelationCommand) -> None:
    settings = Settings()
    engine = engine_for(settings.database_url)
    try:
        if not await check_schema(engine):
            raise AppError(503, "Run migrations first")
        try:
            cipher = PayloadCipher(settings.data_keyring_file)
        except (OSError, ValueError, KeyError):
            raise AppError(503, "Keyring unavailable") from None
        async with sessions_for(engine)() as db, db.begin():
            relation = await propose_relation(db, OperatorContext(), command, cipher)
            relation_id = relation.id
        typer.echo(str(relation_id))
    finally:
        await engine.dispose()


@relations.command("propose")
def propose(
    dominant_id: UUID = typer.Option(...),
    submissive_id: UUID = typer.Option(...),
    scope: list[str] = typer.Option(...),
    agreement_file: Path = typer.Option(...),
) -> None:
    from vowen.cli.main import run

    try:
        if agreement_file.stat().st_size > 40000:
            raise ValueError
        text = agreement_file.read_text(encoding="utf-8")
        command = ProposeRelationCommand.model_validate(
            {
                "dominant_user_id": dominant_id,
                "submissive_user_id": submissive_id,
                "scopes": scope,
                "agreement_text": text,
            }
        )
    except (OSError, ValueError, ValidationError):
        typer.echo(
            "INVALID_INPUT: readable UTF-8 agreement (max 10000 characters) "
            "and valid scopes required",
            err=True,
        )
        raise typer.Exit(1) from None
    run(execute_proposal(command))
