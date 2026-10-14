# Live ingestion operations

The source registry in `data/sources.json` contains 57 public boards verified on October 8, 2026: 33 Greenhouse, 7 Lever, and 17 Ashby. Each entry retains its verification URL and date. Employer identifiers are configuration, never collector logic. Public endpoints can change; source health reports subsequent failures.

## Start collecting

Run from the repository root with the same `DATABASE_URL` as the API:

```sh
python -m alembic upgrade head
python -m collectors.seed_sources
python -m collectors.sync_all --output sync-summary.json
python -m collectors.scheduler
```

The scheduler runs immediately, waits `SYNC_INTERVAL_MINUTES` after a completed pass (default 30), then repeats. Use `--wait-first` to delay the first pass by one interval after a manual sync. Stop with Ctrl+C. A service manager must keep it alive across logout/reboot. No scheduling runs inside the API process. `python -m collectors.scheduler --once` is suitable for smoke checks. `sync_all` exits nonzero if any source failed or was partial, but still attempts other enabled sources. JSON logs and the optional summary file include fetched, created, updated, unchanged, skipped, failed, and closed counters.

`python -m collectors.sync_source SOURCE_ID` targets a registered source. Disabled sources and sources with an unexpired lease return `disabled` or `busy`. `python -m collectors --help` retains the original single-board convenience CLI.

## Register and discover employers

```sh
python -m collectors.seed_sources --file data/sources.json
python -m collectors.seed_sources --file employers.yaml
python -m collectors.discover https://company.example/careers
python -m collectors.registry greenhouse BOARD_TOKEN --company "Employer Name"
```

JSON/YAML imports validate the whole input before writing. Re-importing preserves existing operator settings, including disabled status; use development-only PATCH to change them. The curated seed was live-verified; custom imports are operator-supplied configurations, not automatic discovery activation. POST `/sources` requires a complete nonempty snapshot with normalized postings. Batch discovery records empty reachable endpoints as candidates rather than enabling them. Review full verification output before promoting sources to `data/sources.json`.

Discovery follows at most six redirects per page and two observed same-site careers links. It inspects links, iframes, metadata, and explicit ATS URLs embedded in public markup, then verifies at most five observed candidates. It respects robots rules at every page redirect, applies time/size limits, rejects private addresses and credentials, and never invents a board token or careers path. JavaScript-only or blocked sites can return unknown. This CLI is not exposed as an unauthenticated server-side URL fetch service.

## Lifecycle and consistency

A run first persists a running history row and a per-source lease, then performs HTTP requests outside database write locks. PostgreSQL advisory transaction locks or SQLite `BEGIN IMMEDIATE` serialize writes. Per-posting savepoints isolate normalization failures; retryable database serialization/deadlock/lock errors have a three-attempt budget. Validated batches commit every 100 rows, renewing leases and releasing the writer lock. A failure retains earlier batches; closure reconciliation and final health/history commit only after the snapshot is processed. A crashed worker leaves visible running/interrupted history; after lease expiry another run can recover it. A superseded worker checks its token before each batch.

Only a complete, fully validated snapshot advances missing-job counters. Fetch failures, unexpected shapes, count mismatches, duplicate posting IDs, pagination failures, or any row error skip closure for that source. Valid rows in a partial snapshot can still refresh. Prospect/unlisted posts are intentional skips. Missing active jobs record `missing_since` and increment `consecutive_missing_syncs`.

Defaults close after **3 successful absent snapshots**, or after **72 hours with at least 2 successful absent snapshots**. The latter still requires a second confirmation; elapsed time alone during an outage cannot close jobs. Reappearance clears missing/closed fields, reactivates the same record, and preserves its ID and first discovery time. A surviving duplicate alias is promoted if its canonical posting closes.

Configuration:

| Environment variable    | Default | Purpose                                                  |
| ----------------------- | ------: | -------------------------------------------------------- |
| `STALE_MISSING_SYNCS`   |       3 | Successful absent observations before closure; minimum 2 |
| `STALE_AFTER_HOURS`     |      72 | Time-based grace with two confirmations                  |
| `SOURCE_LEASE_MINUTES`  |      30 | Recovery interval for an abandoned worker                |
| `SYNC_INTERVAL_MINUTES` |      30 | Delay between foreground scheduler passes                |
| `NEW_JOB_HOURS`         |      24 | NEW badge from first discovery, not employer publication |
| `ENABLE_ADMIN_API`      |   false | Enable development mutation endpoints only               |
| `SOURCE_FAILURE_THRESHOLD` | 3 | Consecutive failures before review flag/cooldown |
| `SOURCE_COOLDOWN_MINUTES` | 60 | Retry delay for repeatedly failing sources |
| `WORKDAY_DETAIL_CACHE_HOURS` | 6 | Bounded unchanged-detail cache; zero disables |

Failure count means consecutive failed/partial runs and resets after a full success. Active source counts include all locations, experience levels, and duplicate records; they are not dashboard result counts. A healthy status means the last completed run succeeded; inspect its timestamp to judge recency. History currently has no automatic retention policy.

## Providers and normalization

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html): public list with `content=true`; validates `meta.total` when present, skips prospect posts. `updated_at` stays separate from publication; missing publication/salary remains unknown. No per-job detail crawl.
- [Lever Postings API](https://github.com/lever/postings-api): paginates in batches of 100 until a short page, preserves `createdAt` in UTC, salary interval and workplace type, and normalizes `allLocations`.
- [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api): public board snapshot with compensation enabled, excludes unlisted jobs, normalizes primary/secondary location addresses, and preserves `publishedAt`.
- SmartRecruiters: public listing pagination and per-posting details, with strict complete-snapshot closure safety.
- USAJOBS: official authenticated category-scoped searches and federal/closing metadata.
- Workday: observed tenant/site-specific public CXS POST listing pages and GET details. Listing membership refreshes every run; unchanged details use a bounded cache. See [provider configuration](providers.md).

All adapters throttle requests, use timeouts and retry transport failures/429/5xx up to four total attempts. Raw provider JSON is retained; Workday wrappers additionally record the detail-check timestamp for cache expiry. Structured locations support country/state filtering across multiple locations. Remote alone does not establish U.S. eligibility; cities do not establish onsite work. Text parsing is conservative and incomplete, so some eligible U.S. jobs will be missed when only ambiguous city names appear.

Unchanged jobs are identified by a canonical normalized-content hash and matching
version, using compact source-state queries. Missing legacy hashes initialize by
comparing incoming fields inside the database; no job bodies are returned and
unchanged posting update timestamps are preserved. Observations batch by source
and posting ID. Lifecycle reconciliation excludes seen IDs in SQL. Workday's
six-hour cache is a disposable gzip file restored by Actions, not a full raw-data
query against Neon. See [network measurements and rollout](egress-optimization.md).

Each provider posting upserts on `(source_id, source_job_id)`. Normalized company/title plus matching application identity, or cross-provider identical substantial description and location, groups clear duplicates. Distinct same-board requisitions are retained. Unchanged normalized postings with the current matching version refresh observation timestamps/missing counters without rewriting scores, skills or update times. Changed postings follow the existing matching/upsert pipeline. First discovery never moves on repeat syncs. Employer publication is preserved if a later response omits it.

## Administrative API

Reads: GET `/sources?limit=500&offset=0`, GET `/sources/{id}`, GET `/sources/{id}/history?limit=30&offset=0`. `/sources` in the frontend shows status and the ten latest attempts on demand.

Mutations require **both** `APP_ENV=development` and `ENABLE_ADMIN_API=true`:

- POST `/sources`: company_name, provider, board_token, optional careers_url/enabled.
- PATCH `/sources/{id}`: company_name, careers_url, enabled. Provider/token identity is immutable.
- POST `/sources/{id}/sync`: synchronous single-source result.
- POST `/sync`: synchronous all-source result.

Keep development mutation endpoints on a trusted local interface. They are explicitly blocked in production, even if the enable flag is set. Add authentication, authorization, CSRF/rate-limit protections and an asynchronous admin-job interface before exposing production mutations. Scheduled production ingestion uses the CLI directly; it does not need these endpoints.

## Automated production schedule

`.github/workflows/ingestion.yml` supports manual dispatch and every-30-minute UTC scheduling, with concurrency protection and a 180-minute job timeout. Repository variable `INGESTION_ENABLED=true` is configured in the current deployment. Maintenance shares the same concurrency group, avoiding concurrent scheduled and maintenance writers.

Required secret: `INGESTION_DATABASE_URL`, a persistent hosted PostgreSQL URL with TLS. USAJOBS additionally references `USAJOBS_API_KEY` and `USAJOBS_USER_AGENT` repository secrets. Optional variable: `COLLECTOR_USER_AGENT` with an operator contact. Never put secrets in source JSON or commit `.env`. A production configuration check rejects SQLite or a missing database secret before migration/ingestion.

The workflow applies pending Alembic revisions and idempotently seeds verified configurations before collection; it does not reset data. It uploads the result summary for 14 days; failed/partial results fail visibly. Production uses Neon PostgreSQL and has been exercised through GitHub Actions. The [completion report](mvp-completion.md) records live evidence; a read-only catalog/count audit is available through production maintenance.

[GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) run on the default branch and may be delayed; they are not a strict latency guarantee. Long initial imports serialize, so effective freshness can exceed the trigger interval. Monitor actual source timestamps, failures and interrupted histories before changing cadence or introducing more infrastructure.

Cron example (database credentials supplied securely in the process environment):

```cron
*/30 * * * * cd /srv/gradjobs && .venv/bin/python -m collectors.sync_all >> /var/log/gradjobs-ingestion.log 2>&1
```

Use one scheduling mechanism per environment. SQLite is for local previews and serial writers; PostgreSQL is the production target. SQLite stores JSON and naive UTC timestamps; API serialization restores UTC. PostgreSQL uses JSONB, UUIDs, aware timestamps and advisory locks. Production migration SQL and offline SQLite upgrades/downgrades are tested; actual PostgreSQL execution belongs to the configured CI/service environment.

## Verification and extension

`python -m pytest -q` uses mocked HTTP and captured public fixtures. `RUN_LIVE_TESTS=1 python -m pytest tests/test_live_providers.py -m live -q` opts into nine live boards. On PowerShell set `$env:RUN_LIVE_TESTS='1'` first. These sample employers exist only in test data and the configurable registry.

To add another provider, implement a complete `fetch()` and validated `normalize()` adapter, register it in `collectors/providers.py`, extend provider schema/constants, and add shape/pagination/failure tests. See [live verification](live-ingestion-verification.md) for measured results and limitations.
