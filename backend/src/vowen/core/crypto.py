import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class EncryptedEnvelope:
    key_id: str
    nonce: bytes
    ciphertext: bytes
    format_version: int = 1


def init_keyring(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        PayloadCipher(path)  # validate; never overwrite an existing keyring
        return
    with os.fdopen(fd, "w") as stream:
        json.dump(
            {"active": "k1", "keys": {"k1": base64.b64encode(AESGCM.generate_key(256)).decode()}},
            stream,
        )


class PayloadCipher:
    def __init__(self, path: Path):
        if path.stat().st_mode & 0o077:
            raise ValueError("Keyring permissions must be 0600")
        data = json.loads(path.read_text())
        self.active: str = data["active"]
        self.keys = {
            key: base64.b64decode(value, validate=True) for key, value in data["keys"].items()
        }
        if self.active not in self.keys or any(len(key) != 32 for key in self.keys.values()):
            raise ValueError("Invalid keyring")

    @staticmethod
    def aad(record_type: str, record_id: UUID, schema_version: int) -> bytes:
        return json.dumps(
            [1, record_type, str(record_id), schema_version], separators=(",", ":")
        ).encode()

    def seal_payload(
        self, record_type: str, record_id: UUID, schema_version: int, plaintext: bytes
    ) -> EncryptedEnvelope:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self.keys[self.active]).encrypt(
            nonce, plaintext, self.aad(record_type, record_id, schema_version)
        )
        return EncryptedEnvelope(self.active, nonce, ciphertext)

    def open_payload(
        self, record_type: str, record_id: UUID, schema_version: int, envelope: EncryptedEnvelope
    ) -> bytes:
        if envelope.format_version != 1:
            raise ValueError("Unknown envelope version")
        return AESGCM(self.keys[envelope.key_id]).decrypt(
            envelope.nonce, envelope.ciphertext, self.aad(record_type, record_id, schema_version)
        )
