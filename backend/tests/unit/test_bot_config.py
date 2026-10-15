from vowen.core.config import Settings


def test_inline_dotenv_bot_token_is_secret_and_file_takes_precedence(tmp_path, monkeypatch):
    secret = "synthetic-inline-credential"
    monkeypatch.setenv("BOT_API_TOKEN", secret)
    settings = Settings(_env_file=None)
    assert settings.bot_token() == secret
    assert secret not in repr(settings)
    token_file = tmp_path / "token"
    token_file.write_text("synthetic-file-credential")
    settings = Settings(_env_file=None, telegram_bot_token_file=token_file)
    assert settings.bot_token() == "synthetic-file-credential"
