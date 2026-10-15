# Repository map

[Guide index](README.md) · [Symbol and file index](source-index.md)

Paths below are relative to the repository root. The project is a Python package
and a nested npm application, not a single npm workspace with every command at root.

| Area | Responsibility | First files to read |
| --- | --- | --- |
| `apps/web/app/` | Next.js pages, root layout and global styling | [page.tsx](../../apps/web/app/page.tsx), [layout.tsx](../../apps/web/app/layout.tsx), [globals.css](../../apps/web/app/globals.css) |
| `apps/web/components/` | Client behavior and visible UI | [dashboard.tsx](../../apps/web/components/dashboard.tsx), [job-card.tsx](../../apps/web/components/job-card.tsx) |
| `apps/web/lib/` | Browser API, formatting and status store | [api.ts](../../apps/web/lib/api.ts), [status.ts](../../apps/web/lib/status.ts), [format.ts](../../apps/web/lib/format.ts) |
| `apps/web/types/` | TypeScript JSON contracts | [jobs.ts](../../apps/web/types/jobs.ts) |
| `services/api/app/api/` | HTTP routes and development admin guards | [routes.py](../../services/api/app/api/routes.py), [sources.py](../../services/api/app/api/sources.py) |
| `services/api/app/repositories/` | Search SQL, ingestion writes and provider aggregation | [jobs.py](../../services/api/app/repositories/jobs.py), [ingestion.py](../../services/api/app/repositories/ingestion.py), [providers.py](../../services/api/app/repositories/providers.py) |
| `services/api/app/models/` | Six SQLAlchemy models in one module | [job.py](../../services/api/app/models/job.py) |
| `services/api/app/schemas/` | Pydantic API filters, responses and source validation | [jobs.py](../../services/api/app/schemas/jobs.py), [sources.py](../../services/api/app/schemas/sources.py) |
| `services/api/app/services/` | Source registration persistence | [sources.py](../../services/api/app/services/sources.py) |
| `services/api/app/core/`, `db/` | Environment settings, logging, sessions and SQLite maintenance | [config.py](../../services/api/app/core/config.py), [session.py](../../services/api/app/db/session.py) |
| `services/api/migrations/` | Alembic history and execution environment | [env.py](../../services/api/migrations/env.py) |
| `collectors/` | Provider adapters, discovery, orchestration, operational CLIs | [providers.py](../../collectors/providers.py), [runner.py](../../collectors/runner.py), [sync_all.py](../../collectors/sync_all.py) |
| `collectors/normalizers/` | HTML/text, company/title/URL, location/remote parsing | [text.py](../../collectors/normalizers/text.py), [location.py](../../collectors/normalizers/location.py) |
| `matching/` | Deterministic matching, review, sampling and benchmarks | [scoring.py](../../matching/scoring.py), [experience.py](../../matching/experience.py) |
| `shared/` | Provider/enum literals and normalized payload contract | [constants.py](../../shared/constants.py), [schemas.py](../../shared/schemas.py) |
| `data/` | Reviewed public source registries/candidate provenance | [sources.json](../../data/sources.json) |
| `tests/` | Python fixtures, regression suites and browser DB seed | [conftest.py](../../tests/conftest.py), [seed_browser.py](../../tests/seed_browser.py) |
| `apps/web/tests/`, `e2e/` | Vitest/Testing Library and Playwright | [testing guide](testing.md) |
| `.github/workflows/` | CI, scheduled sync and maintenance | [ci.yml](../../.github/workflows/ci.yml), [ingestion.yml](../../.github/workflows/ingestion.yml), [database.yml](../../.github/workflows/database.yml) |
| Root configuration | Packaging, locks, deployment and local DB | [pyproject.toml](../../pyproject.toml), [vercel.json](../../vercel.json), [docker-compose.yml](../../docker-compose.yml), [alembic.ini](../../alembic.ini) |

## Operational modules that are easy to confuse

- `discover.py` detects and checks a candidate URL; `discover_batch.py` checkpoints
  candidate results without enabling sources.
- `verify_sources.py` verifies and exports records; `registry.py` verifies and
  registers one source. `seed_sources.py` trusts a validated configuration file
  and preserves existing settings; it does not re-fetch all providers.
- `runner.py` runs one source; `sync_source.py` is its registered-ID CLI;
  `__main__.py` accepts a provider/board directly and can create a source.
- `sync_all.py` interleaves providers and records the full run. `scheduler.py`
  repeats it in a foreground process for local/service-managed use.
- `ingestion_state.py` detects unchanged source content. `public_cache.py`
  stores disposable Workday details. These are different caches with different jobs.
- `audit_production.py` checks PostgreSQL metadata/counts. `benchmark_production.py`
  measures HTTP endpoints. `measure_egress.py` estimates row-transfer payloads from
  a local SQLite snapshot; it does not query Neon billing.
- `matching/reprocess.py` recomputes derived fields on stored jobs and can write
  the database. `evaluate.py` evaluates human labels; it does not label examples.

## Generated and private paths

`.venv/`, `node_modules/`, `.next/`, `artifacts/`, local databases, `.vercel/`,
evaluation/reviewer records and `.env` files are not source-of-truth application
code. They are ignored intentionally. A new checkout will not contain private
review labels or the historical local posting database. Use committed public
fixtures for deterministic tests. Do not commit a missing private artifact to
make a documentation command appear reproducible.

`apps/web/AGENTS.md` instructs coding agents to consult the bundled Next.js docs
before frontend implementation changes. This guide adds no frontend code.
