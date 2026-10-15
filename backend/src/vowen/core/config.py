from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://vowen:vowen@localhost:55432/vowen"
    telegram_bot_token: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "BOT_API_TOKEN")
    )
    telegram_bot_token_file: Path | None = None
    telegram_bot_username: str = "vowen_example_bot"
    data_keyring_file: Path = Path("secrets/keyring.json")
    app_display_name: str = "Vowen"
    public_base_url: str = "https://localhost:8443"
    default_timezone: str = "UTC"
    log_level: str = "WARNING"
    app_env: Literal["production", "development", "test"] = "production"
    debug_auth: bool = False

    @model_validator(mode="after")
    def validate_debug_auth(self) -> Self:
        if self.debug_auth:
            public = urlsplit(self.public_base_url)
            database = make_url(self.database_url)
            if (
                self.app_env != "development"
                or public.scheme not in {"http", "https"}
                or public.hostname not in LOCAL_HOSTS
                or public.username is not None
                or public.password is not None
                or public.path not in {"", "/"}
                or public.query
                or public.fragment
                or database.host not in LOCAL_HOSTS
                or not (database.database or "").endswith(("_dev", "_test"))
                or database.query  # libpq host/service overrides must not bypass the host check
            ):
                raise ValueError(
                    "DEBUG_AUTH requires APP_ENV=development, a loopback PUBLIC_BASE_URL "
                    "and a loopback database ending in _dev or _test without URL parameters"
                )
        return self

    def bot_token(self) -> str:
        if self.telegram_bot_token_file is not None:
            return self.telegram_bot_token_file.read_text().strip()
        if self.telegram_bot_token is not None:
            return self.telegram_bot_token.get_secret_value()
        raise RuntimeError("Telegram token is not configured")
