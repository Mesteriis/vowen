import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest
from conftest import BOT_TOKEN, NOW

from vowen.core.errors import AppError
from vowen.modules.auth.telegram_validation import verify_init_data


def signed(telegram_id=100000000001, offset=0, **extra):
    fields = {
        "auth_date": str(int(NOW.timestamp()) + offset),
        "user": json.dumps({"id": telegram_id, "first_name": "Демо & +"}, ensure_ascii=False),
        "query_id": "synthetic",
        **extra,
    }
    secret = hmac.digest(b"WebAppData", BOT_TOKEN.encode(), "sha256")
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_verified_unicode_and_signed_extra_fields():
    identity = verify_init_data(
        signed(signature="synthetic-signature", extra="a+b&c"), BOT_TOKEN, NOW
    )
    assert identity.telegram_id == 100000000001
    reversed_raw = "&".join(
        reversed(signed(signature="synthetic-signature", extra="a+b&c").split("&"))
    )
    assert (
        verify_init_data(reversed_raw, BOT_TOKEN, NOW).assertion_fingerprint
        == identity.assertion_fingerprint
    )


@pytest.mark.parametrize(
    "raw",
    [
        signed(offset=-301),
        signed(offset=31),
        signed() + "&user=%7B%22id%22%3A1%7D",
        signed().replace("hash=", "hash=00"),
        signed(user='{"id":true}'),
        signed(user='{"id":1,"is_bot":true}'),
        signed(user='{"id":"1"}'),
        signed(auth_date="nan"),
        "x" * 17000,
    ],
)
def test_rejects_invalid_proofs(raw):
    with pytest.raises(AppError) as error:
        verify_init_data(raw, BOT_TOKEN, NOW)
    assert error.value.status == 401


def test_boundaries_and_wrong_bot():
    assert verify_init_data(signed(offset=-300), BOT_TOKEN, NOW).telegram_id == 100000000001
    assert verify_init_data(signed(offset=30), BOT_TOKEN, NOW).telegram_id == 100000000001
    with pytest.raises(AppError):
        verify_init_data(signed(), "another-bot", NOW)
