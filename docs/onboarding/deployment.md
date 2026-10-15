# Deployment and scheduled operations

[Guide index](README.md) · [Existing operations reference](../deployment.md) ·
[Verified restoration evidence](../production-restoration.md)

## Actual production layout

The repository root [vercel.json](../../vercel.json) defines two Vercel Services:
Next.js `web` rooted at `apps/web`, and FastAPI `backend` rooted at `.` with
`vercel_app:app`. Import/link the repository at root `.`. Changing Vercel's root
to `apps/web` omits the Python package and root services configuration.

`/api/*` goes to the backend; other routes go to the frontend. The ASGI wrapper
mounts the inner application under `/api`. PostgreSQL is hosted in Neon; Vercel
serves requests but does not own the long ingestion process. GitHub Actions
connects to the same persistent database using a repository secret.

Canonical site: [gradjobs-drab.vercel.app](https://gradjobs-drab.vercel.app).
API base: `https://gradjobs-drab.vercel.app/api`. Generated preview domains may
have Vercel access protection even when the canonical site is public.

## Environment ownership

| Setting | Location / purpose |
| --- | --- |
| `DATABASE_URL` | Vercel backend secret; hosted PostgreSQL, pooled connection suitable for requests |
| `INGESTION_DATABASE_URL` | GitHub Actions secret; mapped to runtime `DATABASE_URL`; unpooled URL suitable for migrations/ingestion |
| `USAJOBS_API_KEY`, `USAJOBS_USER_AGENT` | Actions secrets for federal ingestion; local ignored environment for local work |
| `INGESTION_ENABLED=true` | Repository Actions variable gating maintenance and ingestion jobs |
| `COLLECTOR_USER_AGENT` | Optional repository variable identifying public ingestion |
| `NEXT_PUBLIC_API_URL` | Public web build configuration; leave unset for deployed same-origin `/api` |
| `CORS_ORIGINS` | Backend JSON allowlist of expected frontend origins; production wrapper defaults to canonical origin |
| `APP_ENV`, `ENABLE_ADMIN_API` | Vercel wrapper forces production and admin disabled |

Keep provider TLS requirements such as `sslmode=require`. Do not place connection
strings in source registries, public frontend variables or docs. The backend does
not need federal credentials to serve already stored federal jobs.

## The three workflows

### CI: `.github/workflows/ci.yml`

Push/PR triggers backend, frontend and browser jobs. Backend uses disposable
PostgreSQL 17, upgrades/checks Alembic and runs lint/tests. Frontend runs npm
install/checks/tests/build on Node 24. Browser uses an isolated SQLite seed,
Uvicorn and built Next.js plus Playwright. CI success proves its environments,
not production credentials, billing headroom or actual scheduled delivery.

### Scheduled ingestion: `.github/workflows/ingestion.yml`

Manual dispatch and cron `7,37 * * * *` are enabled. The job gates on the repository
variable, validates PostgreSQL, restores public Workday cache, migrates/seeds,
runs `python -m collectors.sync_all --output sync-summary.json`, saves cache and
uploads the artifact. Cache save can run after partial/failed ingestion when
usable files exist; migration failure does not pretend an import succeeded.

The `gradjobs-ingestion` concurrency group with cancellation disabled serializes
ingestion and database maintenance. This avoids overlap; it is not a guarantee
that every timer trigger executes or completes within 30 minutes. GitHub may delay
or coalesce scheduled activity. The first recovery pass took 37m10s including
setup and initialization; measure later warmed runs separately.

The workflow timeout is three hours. A complete, partial or failed run has a
database history and summary artifact when processing reaches that stage. The
CLI reports partial/failure through a nonzero exit. Always inspect source-level
results; HTTP success or one source's latest timestamp does not prove a full run.

### Maintenance: `.github/workflows/database.yml`

Manual inputs choose `none`, one supported provider, or `failed`. It validates
the persistent database, upgrades Alembic with lock/statement timeouts, seeds
reviewed sources and emits `database-audit.json`. Optional recovery runs one
provider or retries completed sources with errors, restoring/saving Workday
cache where applicable. It shares concurrency with ingestion and has a one-hour
timeout. `failed` still respects runner cooldown/lease controls.

## Safe release sequence

1. Inspect schema changes and production compatibility; complete CI/build checks.
2. Confirm Vercel root/services configuration and server-only environment variables.
3. For DB changes, use Alembic through the maintenance workflow with existing
   secrets. Obtain a backup where practical; never reset or casually downgrade.
4. Deploy the root project using the connected Git deployment or authorized
   `npx vercel --prod` from root. Do not upload local database/artifact files.
5. Verify canonical `/`, `/api/health`, `/api/jobs`, filters, details, apply links,
   local saved searches/tracking, source metadata and operational history.
6. Confirm public mutations remain 403 and unexpected origins are rejected.
7. Inspect the cloud ingestion artifact, schema audit and actual `schedule` event.
   Manual dispatch alone is not evidence of a working timer.

## Cost and failure monitoring

Neon storage, compute and network transfer are separate resources. A small stored
database can still exceed transfer allowance if large ORM rows are repeatedly
downloaded. The current code uses explicit API projections, compact hashes and
public file cache. [Egress estimates](../egress-optimization.md) are local payload
measurements, not billing totals. Compare actual Neon counters over completed
warm runs and real API usage; code cannot refund consumed transfer.

For an outage, inspect `/api/health`, Vercel logs, Neon access/quota and the latest
Actions step before retrying. Do not respond to a quota lock with repeated full
imports, destructive resets, another hosting provider or a silent paid upgrade.
The account owner handles billing choices. See [debugging](debugging.md).
