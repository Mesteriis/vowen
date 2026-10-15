import json
from pathlib import Path

from vowen.core.config import Settings
from vowen.main import create_app


def test_checked_contract_matches_app_and_sanitized_validation_errors():
    schema = create_app(Settings()).openapi()
    checked = json.loads(
        (Path(__file__).resolve().parents[3] / "contracts/openapi.json").read_text()
    )
    assert schema == checked
    response = schema["paths"]["/api/v1/auth/refresh"]["post"]["responses"]["422"]
    assert (
        response["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ErrorResponse"
    )
