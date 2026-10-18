import os
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from vowen.core.crypto import EncryptedEnvelope, PayloadCipher, init_keyring


def test_plain_payloads_need_no_keyring(tmp_path):
    path = tmp_path / "missing-keyring.json"
    codec = PayloadCipher(path)
    row = uuid4()
    data = b"synthetic-private-marker"
    envelope = codec.seal_payload("agreement", row, 1, data)
    assert envelope.key_id == "plaintext-v1" and envelope.nonce == b""
    assert envelope.ciphertext == data
    assert PayloadCipher().open_payload("agreement", row, 1, envelope) == data
    assert not path.exists()
    envelope.nonce = b"invalid"
    with pytest.raises(ValueError):
        codec.open_payload("agreement", row, 1, envelope)
    envelope.nonce = b""
    envelope.format_version = 999
    with pytest.raises(ValueError):
        codec.open_payload("agreement", row, 1, envelope)


def test_legacy_read_only_decoder_and_keyring_binding(tmp_path):
    path = tmp_path / "keyring.json"
    init_keyring(path)
    original = path.read_bytes()
    init_keyring(path)
    assert path.read_bytes() == original and path.stat().st_mode & 0o077 == 0
    codec = PayloadCipher(path)
    codec._load_legacy_keys()
    row = uuid4()
    nonce = os.urandom(12)
    encrypted = AESGCM(codec.keys["k1"]).encrypt(nonce, b"legacy", codec.aad("agreement", row, 1))
    envelope = EncryptedEnvelope("k1", nonce, encrypted)
    assert PayloadCipher(path).open_payload("agreement", row, 1, envelope) == b"legacy"
    with pytest.raises(InvalidTag):
        codec.open_payload("agreement", uuid4(), 1, envelope)
    with pytest.raises(InvalidTag):
        codec.open_payload("agreement", row, 2, envelope)
    with pytest.raises(ValueError):
        PayloadCipher().open_payload("agreement", row, 1, envelope)
