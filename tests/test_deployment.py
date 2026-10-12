from fastapi.testclient import TestClient

from services.api.app.core.config import Settings
from services.api.app.db.session import get_db
from services.api.app.main import app as api_app
from vercel_app import app


def test_vercel_api_prefix_and_production_admin_guard(db, monkeypatch):
    api_app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(
        "services.api.app.api.sources.get_settings",
        lambda: Settings(app_env="production", enable_admin_api=True),
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}
            assert client.get("/api/jobs").status_code == 200
            assert client.get("/api/stats/providers").status_code == 200
            assert client.post("/api/sources", json={}).status_code == 403
    finally:
        api_app.dependency_overrides.clear()


def test_hosted_postgres_urls_use_psycopg():
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
        settings = Settings(
            database_url=prefix + "user:password@db.example/gradjobs?sslmode=require"
        )
        assert settings.database_url == (
            "postgresql+psycopg://user:password@db.example/gradjobs?sslmode=require"
        )
