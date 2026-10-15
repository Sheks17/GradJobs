# Testing strategy

[Guide index](README.md) · [CI workflow](../../.github/workflows/ci.yml)

## What each layer proves

| Layer | Files | Purpose |
| --- | --- | --- |
| Provider fixtures | `tests/test_collectors.py`, `test_workday.py`, `test_phase4a.py`, `test_ats_expansion.py` | Parsing, pagination, malformed/missing payloads, detail errors and retry behavior |
| Normalization/matching | `test_normalization.py`, `test_matching.py`, `test_phase3.py` | Field mappings, experience context, seniority/role/skills and scoring regressions |
| Storage/lifecycle | `test_deduplication.py`, `test_phase2.py`, `test_ingestion_operations.py` | Repeat/changed syncs, aliases, incomplete snapshots, leases/cooldown/history |
| API | `test_api.py` and related phase tests | Contracts, filter combinations, pagination and admin restrictions |
| Egress | `test_egress.py` | Projected SELECTs, unchanged body-read avoidance, fingerprint initialization and cache corruption handling |
| Deployment/migrations | `test_deployment.py`, `test_migrations.py` | Environment guards, schema upgrades and DB behavior |
| Evaluation tools | `test_validation.py` | Human-review contracts, metrics and report handling |
| Frontend units | `apps/web/tests/` | Cards, formatting/storage behavior, provider badges and saved searches |
| Browser | `apps/web/e2e/` | Built app workflows across dashboard, details, tracking, providers and MVP behavior |
| Optional live | `test_live_providers.py`, `test_live_phase4a.py` | Current external endpoint/fixture-contract observations; network-dependent |

Some files span layers; names are historical phases, not independent architecture
modules. Follow the test's assertions rather than inferring coverage from a name.

## Python fixture isolation

[tests/conftest.py](../../tests/conftest.py) creates a disposable in-memory SQLite
database by default. If `TEST_DATABASE_URL` is set, it creates a unique PostgreSQL
schema for each fixture and drops that schema afterward. **Use only an isolated
test database**: fixture teardown is intentionally destructive to its test schema.
Never set `TEST_DATABASE_URL` to production. Workday cache directories are isolated
per test with `tmp_path` to prevent cross-test fixture reuse.

Provider tests inject HTTP clients/mocked transports and sleep functions. This
keeps retry and circuit tests deterministic without calling employers or waiting
through real backoffs. Preserve realistic IDs, missing data and pagination shapes.
Do not include credentials in captured payload fixtures.

## Commands

From root, with a local/test environment:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
```

Run the Alembic commands on the chosen local/disposable DB, not the production URL.
For a collector change, start with its fixture tests plus lifecycle/egress tests.
For a filter change, include API/phase3 tests and corresponding frontend/browser
flows. Broaden only when the change warrants it.

From `apps/web`:

```powershell
npm ci
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

Browser tests expect servers already running; the Playwright config does not
auto-launch them. In a separate explicitly isolated browser-test environment,
set `DATABASE_URL=sqlite:///./artifacts/browser-test.db`, run Alembic and
`python -m tests.seed_browser`, start Uvicorn plus the built frontend and then
run `npm run test:e2e` from the web directory. CI installs Chromium explicitly.
Windows defaults to the Edge channel unless `PLAYWRIGHT_CHANNEL` overrides it;
the viewport is 1440×1000 and failure screenshots go under ignored artifacts.

Optional live suites additionally require their opt-in environment switches;
inspect the skip conditions in the two live test modules before running them.
They are not part of a guaranteed offline regression run. Test results against
real endpoints are time-bounded observations, not enduring provider guarantees.

## Matching evaluation is different

A passing matching unit suite is not precision/recall validation. The evaluator
needs human-labeled sample data, which is intentionally ignored and absent from a
fresh checkout. With an available reviewed dataset:

```powershell
.\.venv\Scripts\python.exe -m matching.evaluate --output data/evaluation/validation.json --markdown docs/phase3-validation.md
```

Do not run that command with invented labels or overwrite a reviewed report with
an unrelated sample. A holdout is exported for human review, not auto-labeled.
Preserve reviewer identity/content integrity checks.

## Recorded baseline, not a new claim

The egress release's recorded CI passed 346 backend tests, 13 frontend tests and
nine browser tests, with 12 optional Python tests skipped. PostgreSQL Alembic
upgrade/check, lint, formatting, TypeScript and production builds passed. See
[the release report](../egress-optimization.md) for its linked CI run. This guide's
creation does not claim to rerun all application tests; documentation checks
validate links, module references and command syntax separately.
