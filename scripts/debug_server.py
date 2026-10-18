"""Run the persistent local UI preview. Never creates or deletes participants on startup."""

import os
from pathlib import Path

import uvicorn
from sqlalchemy.engine import make_url
from vowen.core.config import Settings
from vowen.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    url = os.environ.get("TEST_DATABASE_URL", "")
    target = make_url(url)
    if target.host not in {"127.0.0.1", "localhost", "::1"} or not (
        target.database and target.database.endswith("_test")
    ):
        raise ValueError("Debug preview requires a local _test database")
    runtime = ROOT / "artifacts/deployment/ui-context/runtime"
    token = Path(os.environ.get("DEBUG_BOT_TOKEN_FILE", str(runtime / "bot-token")))
    keyring = Path(os.environ.get("DEBUG_KEYRING_FILE", str(runtime / "keyring.json")))
    if not token.is_file() or not keyring.is_file():
        raise ValueError(
            "Initialize the local token/keyring before starting the debug preview"
        )
    app = create_app(
        Settings(
            app_env="development",
            debug_auth=True,
            database_url=url,
            telegram_bot_token_file=token,
            data_keyring_file=keyring,
            public_base_url="http://127.0.0.1:5176",
        )
    )
    uvicorn.run(app, host="127.0.0.1", port=8002, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
