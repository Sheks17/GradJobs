"""Vercel ASGI entrypoint; the existing API stays available under /api."""

import os

from fastapi import FastAPI

# Vercel deployments must never use development administration or a local database.
if os.environ.get("VERCEL") == "1":
    os.environ["APP_ENV"] = "production"
    os.environ["ENABLE_ADMIN_API"] = "false"
    os.environ.setdefault("CORS_ORIGINS", '["https://gradjobs-drab.vercel.app"]')
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith(("postgresql+psycopg://", "postgresql://", "postgres://")):
        raise RuntimeError("Configure DATABASE_URL with a hosted PostgreSQL URL")

from services.api.app.main import app as api_app  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api_app)
