# GitHub and Vercel deployment

The current design and job features are preserved. `vercel.json` deploys Next.js from `apps/web` and FastAPI from the repository root as Vercel Services. Import the repository with Root Directory `.`; do not change the root to `apps/web`. The first rewrite sends `/api/*` to FastAPI; the second sends page and asset requests to Next.js. Vercel Services is currently beta.

Published repository: https://github.com/Sheks17/GradJobs. Production site: https://gradjobs-drab.vercel.app. The production domain is publicly reachable without signing in; generated preview deployment URLs may retain Vercel authentication.

## Accounts and initial publication

Authenticate the official GitHub and Vercel CLIs with `gh auth login --web` and `npx vercel login`. Never put tokens in source files or pass them in committed commands. With no configured remote, create a public repository named `GradJobs` with `gh repo create GradJobs --public --source . --remote origin --push`. If that name already exists, inspect and reuse the existing repository before pushing; never overwrite its history.

In Vercel, import that repository, or link the root directory with `npx vercel link`. Keep its root at `.` and use the checked-in service configuration. Connect the Git repository for subsequent automatic deployments.

## Production database and secrets

In the Vercel project, open Storage and connect a hosted PostgreSQL database (for example Neon). Select an appropriate plan yourself if account creation or billing is requested. Use a pooled connection for serverless requests. Store `DATABASE_URL` in Vercel's Production environment; a standard `postgresql://` or `postgres://` URL is automatically normalized to the psycopg driver. Use TLS, retaining the provider's `sslmode=require` query parameter. The ASGI entrypoint refuses a missing or SQLite database URL on Vercel and forces production mode with administration disabled.

Leave `NEXT_PUBLIC_API_URL` unset for the same-origin `/api` route. This public variable must never contain secrets. If deploying the API separately, set this variable to its HTTPS origin before rebuilding and configure `CORS_ORIGINS` on that API.

Set these in GitHub → repository Settings → Secrets and variables → Actions:

| Name | Kind | Value |
| --- | --- | --- |
| `INGESTION_DATABASE_URL` | Secret | Hosted database connection; an unpooled URL is suitable for migrations and ingestion |
| `USAJOBS_API_KEY` | Secret | Existing registered USAJOBS key |
| `USAJOBS_USER_AGENT` | Secret | Existing registered email/User-Agent |
| `INGESTION_ENABLED` | Variable | `true` |
| `COLLECTOR_USER_AGENT` | Variable | Optional public collector identity; do not include private credentials |

Run Actions → Scheduled employer ingestion → Run workflow before verifying job search. It migrates the database, registers source configurations, and ingests real postings. A hosted database adds network round trips: the initial import can take substantially longer than the measured local SQLite run. The job allows three hours, and concurrency prevents overlapping full imports. The workflow is scheduled every 30 minutes after activation; GitHub schedules may be delayed and long runs serialize. Do not run collectors inside a Vercel web request or start the foreground scheduler in a serverless function.

The existing local SQLite database is not uploaded. Production is populated from public source boards. To retain exact historic job IDs and first-seen timestamps, perform a separately reviewed database migration rather than committing or bundling a database file.

The twice-hourly trigger uses minutes 7 and 37 UTC to avoid the top-of-hour peak.
This is a best-effort schedule: [GitHub documents delays and dropped scheduled
events under high load](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
Confirm an actual `schedule` event in Actions; a successful manual dispatch proves
cloud ingestion but does not prove that GitHub has delivered a timer event.

For a schema release or targeted recovery, run Actions → Production database maintenance. Choose a provider to retry, `failed` to retry only completed sources with errors, or `none` to migrate without ingestion. Maintenance shares the scheduled-ingestion concurrency group; source leases and database write locks also apply. A read-only `database-audit` artifact reports schema revision, table counts, indexes and JSONB columns without credentials. Migration lock/statement timeouts fail safely rather than waiting indefinitely. The production employment-description column is text so long federal appointment/schedule labels are preserved.

The Workday cache is controlled by `WORKDAY_DETAIL_CACHE_HOURS=6`; source review/cooldown settings are `SOURCE_FAILURE_THRESHOLD=3` and `SOURCE_COOLDOWN_MINUTES=60`. These are optional server/Actions settings, never public credentials. Same-origin production CORS defaults to the canonical HTTPS deployment origin; configure an explicit JSON origin allowlist if the deployment domain changes.

## Build and deploy

Neon network optimization adds migration `c53e0a2026` and compact source-content
fingerprints. Run the additive migration before ingestion when database access is
restored. API list/detail projections remain compatible with the preceding schema.
Workday details are cached in ignored `artifacts/collector-cache` files via GitHub
Actions restore/save, not reloaded from database raw JSON. `COLLECTOR_CACHE_DIR`
optionally selects another local directory. Cache files contain public postings
only; no credentials or personal review records. See [measured egress estimates](egress-optimization.md).

From `apps/web`, run `npm ci`, `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, and `npm run build`. From the root, run `python -m ruff check .`, `python -m ruff format --check .`, and `python -m pytest -q`. Python 3.12 is selected for the API runtime. `requirements.txt` contains runtime dependency versions matching the tested development lock.

Deploy from the root with `npx vercel --prod`. The npm lockfile includes Linux optional dependency peers and was validated in Vercel's Linux build. Public production access is verified independently of authenticated CLI access.

## Live verification and limitations

Verify the real deployment URL after a successful deployment:

1. Open `/` in a signed-out browser; check that listings, statistics, and company options load without localhost requests.
2. Check `/api/health` returns `{"status":"ok","database":"ok"}` and `/api/jobs` returns listings.
3. Search and filter, open a job detail, save a job, and check Saved Jobs and Sources.
4. Confirm `/api/sources` rejects mutation requests with 403 in production.
5. Inspect ingestion workflow success and source/provider health; verify assets and narrow-screen layout.

No working live deployment can be claimed until these checks pass. Before database migration and ingestion, job search and statistics cannot load correctly. Without the USAJOBS secrets, federal ingestion fails; other public providers can still sync. Without `INGESTION_ENABLED=true`, listings are not refreshed automatically. Source administration is intentionally disabled in production. Saved/application states remain local to each browser and do not sync across devices; local development saves do not carry to a different website origin. External application links depend on employer sites and posting expiry. New-provider classification accuracy remains pending human review, as documented in the provider report.

## Publication hygiene

`.gitignore` excludes all `.env` files except examples, local databases/backups, credential files, private exports, evaluation/reviewer records, generated builds, browser test artifacts, and `.vercel`. `.vercelignore` also prevents local secret files and datasets from CLI uploads. Only placeholder development defaults are present in `.env.example`. Never add a production URL containing credentials to the README, workflow, or Vercel configuration.
