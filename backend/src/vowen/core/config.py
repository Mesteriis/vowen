from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    def bot_token(self) -> str:
        if self.telegram_bot_token_file is not None:
            return self.telegram_bot_token_file.read_text().strip()
        if self.telegram_bot_token is not None:
            return self.telegram_bot_token.get_secret_value()
        raise RuntimeError("Telegram token is not configured")
