# Debugging playbook

[Guide index](README.md) · [Flows](flows.md) · [API reference](api.md)

Start with a reproducible symptom and the smallest relevant request. Record time,
environment, source/job UUID and nonsecret error type. Do not paste connection
strings, authorization headers, `.env` or private review notes into bug reports.

## Job service cannot be reached

1. Check the browser's network request destination. Development should call the
   local API root; deployment should call `/api`. A deployed localhost request
   usually means a stale `NEXT_PUBLIC_API_URL` baked into the web build.
2. Check `/health` locally or `/api/health` publicly. 200 proves a simple database
   connection, not current ingestion. 503 means DB access failed; inspect API
   logs and database access/quota before changing filters.
3. If health succeeds but jobs fails, reproduce the exact query against `/jobs`.
   422 points to a validated field; 500 can indicate schema/query/serialization
   problems. Inspect the failing stack without exposing credentials.
4. For local API startup, verify the selected local DB, Alembic revision and
   import path. The API does not create tables automatically. Restart after
   environment changes because settings/engine are initialized and cached.
5. A working `/stats/ats` with null counts is its explicit outage fallback, not
   evidence the database is healthy.

## A known job does not appear

Work through independent gates rather than editing the scorer immediately:

1. Find the registered source's history and latest complete snapshot. Confirm
   the provider ID was returned and normalized, not intentionally skipped.
2. Locate the internal job UUID in a local database or permitted operational
   inspection. A provider ID is not the UUID required by the detail endpoint.
3. Check inactive/deadline status and `duplicate_of`. Closed rows/aliases can be
   returned by detail but are intentionally absent from the public list.
4. Check country in primary/additional locations and normalized role family.
   The normal list excludes `Other`. `country=all` is an API diagnostic option.
5. Broaden seven-day freshness, score, experience and seniority together as needed.
   `include_senior=true` alone does not override score cutoff 50. A five-year
   requirement can cap a score below the normal cutoff.
6. Check skills against `JobSkill`, not just substring text. Check salary
   currency/period and unknown experience exclusions.
7. Reproduce the exact API response. If it contains the job, inspect React
   loading/request-key/abort/render state instead of ingestion.

## Jobs appear old or counts disagree

`posted_at`, `first_seen_at`, `last_seen_at`, `updated_at` and source sync time
are different clocks. Freshness favors a known publication date over discovery.
Unchanged observations preserve `updated_at`. “NEW” means recently discovered.
Check `/ingestion` for a completed full run, not just `/stats`' maximum source
success. Compare like scopes: filtered result total, U.S. stats, global provider
counts and source counts including aliases are not interchangeable.

UTC day/week boundaries can differ from the user's local calendar. Long syncs
can cross midnight. The next scheduled run can change aggregates while you are
writing a report; timestamp the observation instead of claiming a frozen total.

## One provider fails or marks partial

Read `/sources/{id}/history`, source error/cooldown fields and the Actions
`sync-summary` artifact. Distinguish HTTP 429/transient outage, expired board,
invalid payload, duplicate IDs, missing detail, page cap and normalization failure.
Inspect a small public fixture locally. Use injected clients for regressions.
Never mark a truncated response complete to make the workflow green.

For Workday verify observed hostname/shard, tenant, locale and site agree. Confirm
the board token came from `source_token()`. Check circuit and detail cache TTL.
Missing/corrupt cache safely causes a cold fetch; it is not a reason to read all
`Job.raw_data` back from PostgreSQL. A blocked tenant stays documented as blocked.

After a provider recovers, the maintenance workflow can retry one provider or
completed errored sources. Cooldown and active leases still apply. Avoid repeated
manual full runs, credential changes or lease deletion to force progress.

## Ingestion is busy, interrupted or slow

Check the shared Actions concurrency group before assuming a worker is stuck.
At source level an active `sync_token`/unexpired lease returns busy; an expired
lease is reclaimed by the runner and old running history becomes interrupted.
The source lease defaults to 30 minutes and refreshes during write batches.
Read actual progress counters before interfering with a long fetch/import.

Compare `request_count`, latency, rate-limit counts and `upsert_duration_ms`.
Large detail-heavy boards can spend time in HTTP; initialization/changed rows
can spend time in database round trips. A first cold run is not a steady-state
performance benchmark. PostgreSQL advisory locks serialize short write sections;
SQLite uses one in-process writer lock and is not the production concurrency model.

`recover_failed` only selects completed errors with no source token. Its CLI exit
semantics differ from `sync_all`: inspect results/statuses, not exit code alone.
The foreground scheduler also treats partial differently from the full-sync CLI.

## Saved searches or applications disappear

Verify the browser profile and origin, then localStorage keys
`gradjobs:searches:v1` and `gradjobs:status:v1`. Private browsing, blocked/full
storage, cleared data or a different domain can explain loss. Malformed entries
are filtered by parsers. Backend database migration will not restore browser
storage. A tracked job failing to load can leave its status intact; the UI warns
after `Promise.allSettled` and offers retry.

## PostgreSQL schema or cost problems

Use the safe maintenance audit to compare revision, indexes and JSONB columns.
Reproduce migrations on a disposable database. Never `stamp head` or reset
production to hide drift. Check long text handling and SQLite/PostgreSQL JSON
differences before blaming a provider payload.

For egress, inspect query projections and SELECT counts before adding caching
infrastructure. Keep descriptions/raw JSON out of list and unchanged-state reads,
avoid unintended lazy loads, and inspect repeated detail requests on the saved
page. `measure_egress` needs an existing local snapshot and estimates payloads;
it is not an API for current Neon allowance. A quota lock needs account access
restoration; repeated retries cannot repair billing state.

## A test passes locally but fails in CI

Check Python/Node versions, disposable PostgreSQL vs SQLite, JSONB comparisons,
timezone awareness, Linux optional npm dependencies, browser channel/install and
whether servers were started for Playwright. Use lockfiles rather than an
unbounded dependency upgrade. CI fixtures must not depend on ignored local data,
private labels, shared Workday cache or external provider availability.
