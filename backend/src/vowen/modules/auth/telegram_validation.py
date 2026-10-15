import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl

from vowen.core.errors import AppError


@dataclass(frozen=True)
class TelegramIdentity:
    telegram_id: int
    auth_date: datetime
    assertion_fingerprint: str


def verify_init_data(
    raw: str,
    bot_token: str,
    now: datetime,
    max_age_seconds: int = 300,
    future_skew_seconds: int = 30,
) -> TelegramIdentity:
    try:
        if len(raw.encode()) > 16384 or re.search(r"%(?![0-9A-Fa-f]{2})", raw):
            raise ValueError
        pairs = parse_qsl(
            raw, keep_blank_values=True, strict_parsing=True, errors="strict", max_num_fields=64
        )
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise ValueError
        signature = fields.pop("hash")
        if not re.fullmatch("[0-9a-fA-F]{64}", signature):
            raise ValueError
        check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret = hmac.digest(b"WebAppData", bot_token.encode(), "sha256")
        expected = hmac.digest(secret, check.encode(), "sha256")
        if not hmac.compare_digest(expected, bytes.fromhex(signature)):
            raise ValueError
        if not fields["auth_date"].isascii() or not fields["auth_date"].isdigit():
            raise ValueError
        auth_date = datetime.fromtimestamp(int(fields["auth_date"]), UTC)
        age = (now - auth_date).total_seconds()
        user = json.loads(fields["user"])
        telegram_id = user["id"]
        if (
            age > max_age_seconds
            or age < -future_skew_seconds
            or type(telegram_id) is not int
            or not 0 < telegram_id < 2**63
            or user.get("is_bot", False) is not False
        ):
            raise ValueError
        fingerprint = hashlib.sha256(secret + expected).hexdigest()
        return TelegramIdentity(telegram_id, auth_date, fingerprint)
    except (ValueError, KeyError, TypeError, OverflowError, OSError):
        raise AppError(401, "INVALID_AUTH") from None
