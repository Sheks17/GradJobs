# Run locally

[Guide index](README.md) · [Testing](testing.md) · [Deployment](deployment.md)

Use Python 3.12 or later (CI/deployment use 3.12), Node 24 as in CI, npm and Git.
Docker is optional for SQLite but needed for the provided local PostgreSQL service.
Commands below are PowerShell from the repository root unless stated otherwise.
They contain only development defaults; never substitute production credentials
into committed command files.

## 1. Install Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Using the explicit interpreter avoids needing to change PowerShell execution
policy. On macOS/Linux the interpreter is `.venv/bin/python`; activate the venv
or use that path. Keep an existing `.env` intact and edit only needed values.
`requirements-dev.lock` is the tested development dependency set; `requirements.txt`
is the deployed runtime set; `pyproject.toml` defines package metadata/ranges.

## 2. Choose one local database

### PostgreSQL (closest to production)

The copied `.env.example` points to the development database exposed by
[docker-compose.yml](../../docker-compose.yml). Its credentials are local defaults.

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Check `DATABASE_URL` is the local database before migrations. If your shell already
has that variable set, it takes precedence over `.env`. Do not print a production
URL while diagnosing configuration. Docker data uses a named volume; do not remove
that volume to fix a schema mismatch without first understanding the data loss.

### SQLite (explicit lightweight alternative)

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
$env:DATABASE_URL = 'sqlite:///./artifacts/onboarding.db'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

This sets the current shell only. Use the same value in each Python terminal, or
put it in the ignored root `.env` for a persistent local choice. SQLite is not
selected automatically when PostgreSQL is unavailable. Never use this fallback
for production ingestion; `collectors.production_check` rejects it.

## 3. Populate intentionally

For offline exploration, use clearly labeled fictional data:

```powershell
.\.venv\Scripts\python.exe -m services.api.app.seed
```

Demo jobs are excluded by default. Enable the demo filter in the dashboard and
broaden filters if needed; their application links are intentionally nonworking.
Do not present demo jobs as live vacancies. Browser regression fixtures are a
different dataset owned by `tests.seed_browser`, not production seed data.

For real public data, source registration and syncing make outbound requests:

```powershell
.\.venv\Scripts\python.exe -m collectors.seed_sources
.\.venv\Scripts\python.exe -m collectors.sync_all --provider greenhouse --limit 1 --output artifacts/local-sync.json
```

The seed imports the reviewed `data/sources.json` configuration. A full sync covers
many employers and may take substantial time. Start with one source/provider.
USAJOBS requires its registered key/User-Agent in the ignored environment; a missing
federal key does not prevent working on public-provider fixtures. Do not put keys
inside `provider_config` or paste them into terminal output.

## 4. Start API and frontend in separate terminals

API, from the repository root, with the selected local DB environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.app.main:app --reload --port 8000
```

Frontend, from the repository root in another terminal:

```powershell
Set-Location apps/web
npm ci
npm run dev
```

The default development API base is `http://localhost:8000`; create a private
`apps/web/.env.local` from the web example only if overriding it. The root backend
`.env` is not automatically the Next.js app's environment file. Open
`http://localhost:3000`, `http://localhost:8000/health` and
`http://localhost:8000/docs`. A missing `/api` prefix locally is expected.
Changing `NEXT_PUBLIC_API_URL` requires restarting/rebuilding the web app.

## 5. First bounded checks

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_collectors.py tests/test_api.py -q
.\.venv\Scripts\python.exe -m alembic check
```

Run npm commands in `apps/web`; run Python commands at root. The default admin API
is disabled even in development. Enable `ENABLE_ADMIN_API=true` only in a local
development environment if testing mutations. Keep it off in deployment.

To stop, use Ctrl+C in API/frontend terminals. `docker compose stop db` preserves
local database data. Do not use a production database for onboarding exercises,
test seeds, migration downgrade practice or test fixture schemas.
