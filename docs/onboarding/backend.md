# Backend architecture

[Guide index](README.md) · [Endpoint reference](api.md) · [Database](database.md)

## Entry points and dependencies

[services/api/app/main.py](../../services/api/app/main.py) constructs the inner
FastAPI app, configures JSON logging and CORS, and includes the read and source
routers. It does not create database tables, run Alembic or start collectors at
startup. Locally Uvicorn imports `services.api.app.main:app`. Production imports
[vercel_app:app](../../vercel_app.py), which guards the environment and mounts the
inner app at `/api`.

[core/config.py](../../services/api/app/core/config.py) defines Pydantic settings
loaded from environment and `.env`, with a cached `get_settings()`. Standard
PostgreSQL URL prefixes are normalized to the psycopg SQLAlchemy driver. The
default database is local PostgreSQL, not automatic failover to SQLite. Selecting
SQLite requires an explicit `DATABASE_URL`. Restart a process after changing
settings; engine creation and settings caching happen on import.

[db/session.py](../../services/api/app/db/session.py) builds the engine with
`pool_pre_ping=True`, `SessionLocal(expire_on_commit=False)`, the declarative Base,
and `utcnow()`. The `get_db` dependency yields a request-scoped session and closes
it afterward. It does not auto-commit writes. Routes, services or runners commit
explicitly. SQLite enables WAL and foreign keys on each connection.

## Layers

| Layer | Example | Responsibility |
| --- | --- | --- |
| HTTP route | `api/routes.py::jobs` | Bind/validate request and return response contract |
| Pydantic contract | `schemas/jobs.py::JobFilters`, `JobPage` | Types, bounds, response serialization |
| Read repository | `repositories/jobs.py::list_jobs` | Build/filter/order/paginate SQL |
| Write repository | `repositories/ingestion.py::upsert_job` | Store normalized data, matching and duplicate references |
| Source service | `services/sources.py::register_source` | Idempotent creation by provider/board |
| ORM model | `models/job.py::Job` | Persistent columns, constraints, indexes |

Collectors reuse the backend model/session/write repository. They are not a
separate duplicated database model. `shared/schemas.py::NormalizedJob` is the
provider-to-persistence contract; it is different from the public `JobSummary`.

## Read paths

`/jobs` delegates to `list_jobs`, which performs a count and a bounded page query.
It selects fields in `JobSummary.model_fields` with `load_only(..., raiseload=True)`.
`/jobs/{UUID}` selects `JobDetail` fields. Descriptions are fetched only for detail;
raw provider JSON and internal bookkeeping are omitted from both responses.
An accidental access to an omitted ORM column raises rather than quietly causing
another body fetch. Maintain this projection when evolving response models.

`/stats` uses SQL aggregates over visible U.S. jobs, while provider statistics
aggregate canonical active non-demo jobs across countries. `provider_statistics`
in [repositories/providers.py](../../services/api/app/repositories/providers.py)
uses a window function to select the latest attempt per source, then groups
counts and request costs. Those attempts can belong to different full runs.
“Healthy” means enabled, with a prior successful sync and no last error; it does
not by itself mean this source completed the latest full run.

`/stats/ats` merges that operational data with the static ATS capability registry.
It catches database errors, rolls back, and reports unavailable counts as null.
Most other data endpoints propagate failures; `/health` explicitly returns 503 on
database failure. A working registry page can therefore coexist with an outage.

## Write paths and administration

The source router's `development_admin()` dependency requires both
`APP_ENV=development` and `ENABLE_ADMIN_API=true`. It protects create, patch,
source sync and full sync endpoints. In production, those endpoints return 403;
there is no user/admin login or production token scheme implemented.

Source registration verifies public payloads in the CLI or create endpoint before
persistence. The lower-level `register_source()` does not fetch the board itself.
The seed command validates trusted configuration and calls this service; existing
source settings are preserved rather than overwritten on each scheduled run.

Ingestion runs HTTP fetches outside write transactions, then uses locks,
savepoints and batches. See [ingestion](ingestion.md) for failure isolation and
transaction ownership. Do not call a long source sync from a production web request.
