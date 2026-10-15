from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from vowen.core.crypto import PayloadCipher, init_keyring


def test_keyring_idempotent_and_envelope_binding(tmp_path):
    path = tmp_path / "keyring.json"
    init_keyring(path)
    original = path.read_bytes()
    init_keyring(path)
    assert path.read_bytes() == original
    assert path.stat().st_mode & 0o077 == 0
    cipher = PayloadCipher(path)
    row = uuid4()
    envelope = cipher.seal_payload("agreement", row, 1, b"synthetic-private-marker")
    assert b"synthetic-private-marker" not in envelope.ciphertext
    assert cipher.open_payload("agreement", row, 1, envelope) == b"synthetic-private-marker"
    assert (
        envelope.ciphertext
        != cipher.seal_payload("agreement", row, 1, b"synthetic-private-marker").ciphertext
    )
    with pytest.raises(InvalidTag):
        cipher.open_payload("agreement", uuid4(), 1, envelope)
    with pytest.raises(InvalidTag):
        cipher.open_payload("agreement", row, 2, envelope)
    envelope.key_id = "missing"
    with pytest.raises(KeyError):
        cipher.open_payload("agreement", row, 1, envelope)
