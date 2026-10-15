import asyncio
from collections.abc import Coroutine
from typing import Any

import typer
from sqlalchemy import select

from vowen.cli.relations import relations
from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.crypto import init_keyring
from vowen.core.database import check_schema, engine_for, sessions_for
from vowen.core.errors import AppError
from vowen.modules.auth.service import revoke_user_sessions
from vowen.modules.identity.models import User
from vowen.modules.identity.service import ProvisionUserCommand, create_user, set_user_active

app = typer.Typer(pretty_exceptions_enable=False)
users = typer.Typer()
instance = typer.Typer()
app.add_typer(users, name="users")
app.add_typer(instance, name="instance")
app.add_typer(relations, name="relations")


async def execute_user(action: str, telegram_id: int = 0, display_name: str = "") -> None:
    engine = engine_for(Settings().database_url)
    try:
        if not await check_schema(engine):
            raise AppError(503, "Run migrations first")
        async with sessions_for(engine)() as db, db.begin():
            if action == "create":
                user = await create_user(
                    db,
                    ProvisionUserCommand(telegram_id=telegram_id, display_name=display_name),
                    Clock().now(),
                )
                typer.echo(str(user.id))
            elif action in ("enable", "disable"):
                await set_user_active(db, telegram_id, action == "enable", Clock().now())
            elif action == "revoke-sessions":
                user = await db.scalar(
                    select(User).where(User.telegram_id == telegram_id).with_for_update()
                )
                if user is None:
                    raise AppError(404, "NOT_FOUND")
                await revoke_user_sessions(db, user.id)
            elif action == "list":
                for user in (await db.scalars(select(User))).all():
                    typer.echo(
                        f"{user.id}\t{user.telegram_id}\t{user.display_name}\t{user.is_active}"
                    )
    finally:
        await engine.dispose()


def run(coro: Coroutine[Any, Any, None]) -> None:
    try:
        asyncio.run(coro)
    except AppError as error:
        typer.echo(error.code, err=True)
        raise typer.Exit(1) from None


@instance.command("init")
def init() -> None:
    init_keyring(Settings().data_keyring_file)
    typer.echo("Keyring ready; existing keys preserved")


@users.command("create")
def create(telegram_id: int = typer.Option(...), display_name: str = typer.Option(...)) -> None:
    run(execute_user("create", telegram_id, display_name))


@users.command("disable")
def disable(telegram_id: int = typer.Option(...)) -> None:
    run(execute_user("disable", telegram_id))


@users.command("enable")
def enable(telegram_id: int = typer.Option(...)) -> None:
    run(execute_user("enable", telegram_id))


@users.command("revoke-sessions")
def revoke(telegram_id: int = typer.Option(...)) -> None:
    run(execute_user("revoke-sessions", telegram_id))


@users.command("list")
def listing() -> None:
    run(execute_user("list"))
