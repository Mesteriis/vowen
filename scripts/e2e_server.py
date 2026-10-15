"""Synthetic-only test server, no production authentication bypass."""
import asyncio
import os
from pathlib import Path
import uvicorn
from sqlalchemy import text
from vowen.core.clock import Clock
from vowen.core.config import Settings
from vowen.core.crypto import init_keyring
from vowen.core.database import engine_for, sessions_for
from vowen.modules.identity.service import create_user, ProvisionUserCommand
from vowen.main import create_app

root = Path(__file__).resolve().parents[1]
url = os.environ.get('TEST_DATABASE_URL','postgresql+psycopg://vowen:vowen@127.0.0.1:55432/vowen_test')
if not url.rsplit('/',1)[-1].endswith('_test'):
    raise RuntimeError('E2E requires a disposable _test database')
folder = root / 'web/test-results'
folder.mkdir(exist_ok=True)
token = folder / 'bot-token'
token.write_text('123456:synthetic_test_token_not_a_real_credential')
token.chmod(0o600)
keyring = folder / 'keyring.json'
init_keyring(keyring)

async def seed():
    engine = engine_for(url)
    try:
        async with sessions_for(engine)() as db, db.begin():
            await db.execute(text('TRUNCATE users CASCADE'))
            for i in range(6):
                await create_user(db, ProvisionUserCommand(telegram_id=100000000201+i,display_name=f'Demo {i+1}'),Clock().now())
    finally:
        await engine.dispose()

asyncio.run(seed())
app = create_app(Settings(database_url=url,telegram_bot_token_file=token,data_keyring_file=keyring,public_base_url="http://127.0.0.1:5174"))
uvicorn.run(app,host='127.0.0.1',port=8001,access_log=False,log_level='warning')
