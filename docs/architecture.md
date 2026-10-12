# Architecture

```text
Public employer ATS endpoints
        ↓ HTTP with timeout, throttle, bounded retry
Provider collectors → normalized Pydantic Job
        ↓ text/location/URL normalization
Rule-based classification and scoring
        ↓ conservative duplicate candidates + transactional upsert
PostgreSQL (jobs, job_sources, source_syncs, job_locations; raw JSONB retained)
        ↓ SQLAlchemy query layer
FastAPI (validated filters, stable pagination, summaries)
        ↓ browser fetch
Next.js dashboard → employer's original application site
        ↘ browser-local application status
```

## Boundaries

The frontend only reads the API and owns the Phase 1 browser-local tracking state. It never accesses PostgreSQL, embeds database credentials, calls provider APIs, or runs collectors. Its production build does not require a running API. The browser needs a reachable `NEXT_PUBLIC_API_URL` and a matching API CORS origin.

Collectors are ordinary Python adapters and a CLI. Scheduled collectors run separately from API reads. Explicit development-only mutation endpoints can also run synchronous collection. The runner can be invoked from cron, a cloud scheduler, GitHub Actions, or a future worker without changing parsing logic. There is no hidden scheduling or background loop at API startup.

The shared ingestion contract validates required identity and safe HTTP(S) links before persistence. Provider raw JSON is retained unchanged. Descriptions are converted to plain text; React renders them as text, never as untrusted HTML. The matching package has no database or networking dependency; its title normalization import is also a pure function.

## Storage

`job_sources`: unique provider/board pair, company, URLs, enabled flag, last attempt, last complete success, and safe diagnostic summary. A `manual/demo` source is explicitly disabled for automated ingestion.

`jobs`: source identity, source/apply URLs, employer metadata, raw and normalized title/location, description fingerprint, salary amount/currency/period, nullable experience bounds and original match, seniority, family, score/label/reasons, source publication/update dates, first/last observation, active/closed state, raw JSONB, demo flag, and nullable `duplicate_of` foreign key.

The `(source_id, source_job_id)` uniqueness constraint makes repeated syncs idempotent within a board. A duplicate remains a separate source record so its provenance and freshness are never overwritten by another provider. Discovery hides aliases (`duplicate_of IS NOT NULL`). The initial rule does not attempt fuzzy matching.

PostgreSQL uses UUIDs, numeric monetary amounts, JSONB, and timezone-aware timestamps. SQLAlchemy uses JSON in SQLite for offline testing only. The initial Alembic migration is a static schema snapshot, independent of future ORM changes. Production startup never calls `create_all`.

## Consistency and failure handling

A per-source expiring lease prevents overlapping board runs. PostgreSQL advisory locks (or SQLite immediate transactions) serialize writes, with network fetches outside those locks. Completed job changes, lifecycle reconciliation, health, and history commit together. Expired workers are fenced by a token. Each posting gets a savepoint; malformed postings cannot roll back other valid postings. A partial run records an error and does not advance `last_successful_sync`. Complete fetch failures never trigger closure or deletion. A source-level terminal database error still requires operator attention.

API requests use short-lived sessions. Queries return active canonical U.S. jobs by default, with title-based technology families and conservative early-career thresholds. Unknown country is excluded from the default instead of being mislabeled U.S. Multiple indexes support common filters. SQL substring search is intentionally simple; add PostgreSQL full-text/trigram indexing after measuring realistic ingestion volumes.

## UI and tracking

Discovery has explicit loading, empty, and error states. Requests are abortable, and stale responses cannot replace newer filters. Unknown posting dates use a labeled discovery date. Demo roles never expose fake application actions. The user can inspect exact scoring reasons on each detail page.

Application status is stored as a versioned ID-to-status map in localStorage. Reads validate state, handle corrupted JSON, and subscribe to cross-tab changes. Explicit write failures are shown. No claims of cloud sync or account identity are made. A future authenticated API can replace this small adapter without changing ingestion.

## Deployment boundary

Development source mutations require APP_ENV=development and ENABLE_ADMIN_API=true; production mutations are blocked pending authentication. The read-only source page exposes health and sync history. Deploy the read-only API and frontend separately with TLS, configured origins, managed secrets, database backups, migration rollout, and an operator-run collector schedule. Source health is public metadata; do not put secrets in source names, URLs, or error summaries. See `infrastructure/README.md`.

Phase 2 adds normalized JSON location arrays plus indexed `job_locations` rows, `missing_since` and consecutive successful absence counts, source health counters, expiring sync leases, and persisted `source_syncs`. The foreground scheduler and GitHub Actions workflow call the same sync-all service. See [ingestion operations](ingestion.md).
