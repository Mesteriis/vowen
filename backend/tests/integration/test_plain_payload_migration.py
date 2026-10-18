import os
import runpy
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text

from vowen.core.crypto import PayloadCipher, init_keyring


async def prepare(connection, migration, path, corrupt=False):
    init_keyring(path)
    codec = PayloadCipher(path)
    codec._load_legacy_keys()
    for name, kind in migration["BINDINGS"].items():
        await connection.execute(
            text(
                f"CREATE TEMP TABLE {name} (id uuid PRIMARY KEY, key_id text, "
                "nonce bytea, ciphertext bytea) ON COMMIT DROP"
            )
        )
        uid = uuid4()
        nonce = os.urandom(12)
        data = AESGCM(codec.keys["k1"]).encrypt(nonce, b"synthetic legacy", codec.aad(kind, uid, 1))
        if corrupt and name == "change_requests":
            data = data[:-1] + bytes([data[-1] ^ 1])
        for key_id, record, iv, payload in (
            ("k1", uid, nonce, data),
            ("plaintext-v1", uuid4(), b"", b"already plain"),
            (None, uuid4(), None, None),
        ):
            await connection.execute(
                text(f"INSERT INTO {name} VALUES (:id,:key,:nonce,:data)"),
                {"id": record, "key": key_id, "nonce": iv, "data": payload},
            )
    await connection.execute(
        text(
            "CREATE TRIGGER currency_entries_immutable BEFORE UPDATE OR DELETE "
            "ON pg_temp.currency_entries FOR EACH ROW "
            "EXECUTE FUNCTION public.currency_entries_immutable()"
        )
    )


async def test_plain_migration_covers_all_payload_types_and_needs_no_key_afterwards(api, tmp_path):
    _, app = api
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0035_plain_payloads.py")
    )
    path = tmp_path / "legacy-keyring.json"
    async with app.state.engine.begin() as connection:
        await prepare(connection, migration, path)
        await connection.run_sync(lambda sync: migration["convert"](sync, path))
        path.unlink()
        await connection.run_sync(lambda sync: migration["convert"](sync, path))
        for name in migration["BINDINGS"]:
            rows = (
                await connection.execute(
                    text(f"SELECT key_id,nonce,ciphertext FROM {name} WHERE ciphertext IS NOT NULL")
                )
            ).all()
            assert len(rows) == 2
            assert all(row.key_id == "plaintext-v1" and row.nonce == b"" for row in rows)
            assert {bytes(row.ciphertext) for row in rows} == {
                b"synthetic legacy",
                b"already plain",
            }
        with pytest.raises(Exception, match="immutable"):
            async with connection.begin_nested():
                await connection.execute(
                    text("UPDATE pg_temp.currency_entries SET ciphertext='changed'")
                )


async def test_corrupt_legacy_payload_rolls_back_all_conversion_and_trigger_changes(api, tmp_path):
    _, app = api
    migration = runpy.run_path(
        str(Path(__file__).parents[2] / "migrations/versions/0035_plain_payloads.py")
    )
    path = tmp_path / "legacy-keyring.json"
    async with app.state.engine.begin() as connection:
        await prepare(connection, migration, path, corrupt=True)
        with pytest.raises(RuntimeError, match="original data keyring"):
            async with connection.begin_nested():
                await connection.run_sync(lambda sync: migration["convert"](sync, path))
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM pg_temp.relation_versions WHERE key_id='k1'")
            )
            == 1
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT tgenabled FROM pg_trigger WHERE "
                    "tgrelid='pg_temp.currency_entries'::regclass "
                    "AND tgname='currency_entries_immutable'"
                )
            )
            == "O"
        )
