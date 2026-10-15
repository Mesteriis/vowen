from fastapi.testclient import TestClient

from vowen.core.config import Settings
from vowen.main import create_app


def test_liveness_does_not_need_telegram():
    app = create_app(Settings(database_url="postgresql+psycopg://invalid:invalid@127.0.0.1:1/no"))
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200


def test_readiness_fails_for_unavailable_database():
    app = create_app(Settings(database_url="postgresql+psycopg://invalid:invalid@127.0.0.1:1/no"))
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert "invalid" not in response.text
