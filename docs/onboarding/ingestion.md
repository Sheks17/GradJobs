# Collectors, normalization and ingestion

[Guide index](README.md) · [Job walkthrough](flows.md#follow-one-job-through-gradjobs)

## Provider contract

[Collector](../../collectors/base.py) is the shared abstract HTTP adapter. A
collector receives a validated board identifier, employer display name, optional
public configuration and optionally an injected HTTP client/sleep function for
tests. `fetch()` returns a source snapshot; `normalize(raw)` returns a validated
`NormalizedJob`, returns `None` for an intentional exclusion, or raises on bad data.
`snapshot_complete` must become false if any required portion could not be fetched.
Call `close()` to release clients the collector owns.

[providers.py](../../collectors/providers.py) maps names to executable classes and
careers URL templates. [ats_registry.py](../../collectors/ats_registry.py) describes
the larger support/detection matrix. The shared literal types constrain accepted
provider values. All three surfaces matter when adding an adapter.

| Adapter module | Fetch shape / important mapping |
| --- | --- |
| [greenhouse.py](../../collectors/greenhouse.py) | Board jobs with content; checks reported total; excludes talent-pool rows with null internal job ID; uses provider ID and absolute URL |
| [lever.py](../../collectors/lever.py) | Pages of 100 with skip/limit; joins description/list/additional sections; converts created milliseconds and disclosed salary interval |
| [ashby.py](../../collectors/ashby.py) | Posting API with compensation; excludes explicitly unlisted jobs; handles structured address and secondary locations |
| [smartrecruiters.py](../../collectors/smartrecruiters.py) | Offset pages then detail calls for job-ad sections; incomplete details mark partial; optional country-scoped board |
| [usajobs.py](../../collectors/usajobs.py) | Keyed official search; 1–12 scoped queries; page bounds and cross-query ID deduplication; qualifications, eligibility, closing date and remuneration |
| [workday.py](../../collectors/workday.py) | Tenant/site-specific public CXS POST pages of 20 and bounded details; stable detail ID plus requisition ID; see below |
| [workable.py](../../collectors/workable.py) | Public widget plus public detail; validates published/noninternal identity; shortcode ID; no private recruiter SPI API |
| [recruitee.py](../../collectors/recruitee.py) | Public offers feed with descriptions/requirements, locations, dates and structured salary |
| [breezyhr.py](../../collectors/breezyhr.py) | Public JSON listing plus exactly one schema.org JobPosting from employer HTML; validates links/structured identity; missing structured details make partial |

Shared [public_feeds.py](../../collectors/public_feeds.py) rejects unexpected
pagination or reported-total mismatches rather than silently treating a truncated
feed as complete. It also validates same-board HTTPS links and explicit salary/date
values. Capability flags describe supported mappings, not guaranteed fields on
every posting.

## Workday's separate treatment

`workday_config()` observes an HTTPS host such as a tenant's
`<tenant>.wd<number>.myworkdayjobs.com`, optional locale and site path. It does not
guess from the company name or assume one `wd5` shard. `source_token()` includes
hostname and site to avoid collisions, and configuration must agree with the URL.
The CXS base includes `/wday/cxs/<tenant>/<site>`.

The first page establishes the total. Later pages may report zero total while
still returning jobs, an observed CXS behavior explicitly handled in the parser.
Repeated paths, changing totals, missing pages and page-limit exhaustion cannot
be accepted as a complete snapshot. Details supply descriptions, stable IDs,
time type, start/end dates, additional locations and raw content.

There are two detail workers per Workday board and a default provider concurrency
of one board. Five consecutive detail failures open an in-run circuit; closures
are then skipped. The six-hour cache reuses a detail only when the stable summary
matches; relative `postedOn` text alone does not invalidate it. Description-only
changes can therefore wait until the TTL. Date-only values use explicit UTC
handling; salary parsing requires explicit currency/range and period evidence.

[public_cache.py](../../collectors/public_cache.py) persists disposable gzip JSON
under ignored `artifacts/collector-cache` or `COLLECTOR_CACHE_DIR`. Corrupt/oversized
caches are ignored, invalid normalized details are excluded, and cache-write
failure cannot fail valid ingestion. GitHub Actions restores/saves these public
files; Neon raw JSON is no longer downloaded to hydrate the cache.

## Normalization boundary

[NormalizedJob](../../shared/schemas.py) forbids extra fields, strips surrounding
strings, validates length/URL/date/salary contracts and preserves `raw_data`.
URLs must be HTTP(S) and contain no credentials; provider-specific helpers apply
tighter host/path checks. Dates require timezones after adapter conversion.

[normalizers/text.py](../../collectors/normalizers/text.py) unescapes HTML, removes
script/style, produces plain text, standardizes title/company strings and removes
known tracking query parameters without stripping requisition identifiers.
[normalizers/location.py](../../collectors/normalizers/location.py) normalizes
country/state/city, primary/additional locations, remote type and explicit remote
restrictions. Ambiguous bare country/state abbreviations are handled
conservatively. Provider metadata can preserve structured restrictions; otherwise
upsert derives them from location/description text.

## One source transaction path

`runner.sync_source()` obtains a short write lock, resolves/creates the source,
checks enabled/cooldown/lease state, records an attempt and commits its lease.
It then fetches HTTP outside the write transaction. Before writes it verifies the
lease token still belongs to this worker.

It loads compact source state: provider job ID, eligible content hash, posting
date and deadline. For each normalized row:

1. `None` is an intentional skip; repeated IDs in one snapshot are failures.
2. `ingestion_state.unchanged()` compares a canonical SHA-256 hash of normalized
   source content, including real raw content and dates, excluding derived remote
   fields and Workday's internal cache-check timestamp.
3. An unchanged active/current-version job skips classification/upsert. Observation
   updates preserve `updated_at`, reset missing state and refresh `last_seen_at`.
4. Legacy null hashes are initialized by a server-side equality UPDATE; stored
   descriptions/raw JSON are not downloaded for this comparison.
5. New/changed/inactive/outdated-version rows use `upsert_with_retry()` and
   `repositories/ingestion.py::upsert_job()`.

The runner commits validated batches every 100 input rows and refreshes the source
lease. Unchanged observation IDs are updated in groups of at most 500. Savepoints
isolate individual upserts. PostgreSQL serialization/deadlock/lock errors with
SQLSTATE `40001`, `40P01`, or `55P03` are retried up to three attempts; permanent
database errors are not blindly retried. A later source failure does not undo
earlier committed batches. Partial snapshots preserve valid writes but do not
perform missing-job closure reconciliation.

## Upsert and duplicate handling

Upsert finds the exact source/job pair, computes normalized duplicate keys and
matching evidence, looks for a duplicate candidate, then inserts/updates the row
and replaces location/skill rows. Missing later posting/deadline values preserve
known dates. A deadline already passed makes the row inactive.

Candidate duplicates must have the same normalized company/title/demo status and
be active canonical rows. Either normalized apply URL or description fingerprint
must match. Conflicting known location strings disqualify a candidate. A shared
apply URL is sufficient after those checks. A description-only match additionally
requires different providers, at least 160 incoming description characters, and
the same nonempty normalized location. Candidates are ordered by first seen/ID.

The duplicate row is retained with `duplicate_of`; list queries hide aliases.
This is conservative exact-key grouping, not fuzzy semantic deduplication. Company
suffix normalization is not a legal-entity/acquisition identity service. Distinct
boards remain distinct sources even when their jobs normalize to one company.

## Lifecycle and failure protection

[lifecycle.py](../../collectors/lifecycle.py) increments missing counters only after
a complete, fully normalized snapshot. Defaults close after three complete misses,
or after at least two misses and 72 hours missing. A successful observation clears
missing state. Explicit deadlines are expired separately, retained rows are not
deleted, and an active duplicate alias is promoted if its canonical closes.

`failure_count` is the actual source field name. Errors increment it, record
timestamps/error text and flag review via `disabled_reason`; they do not silently
delete/disable the source. At threshold three, attempts wait for a default 60-minute
cooldown. A success resets the counter/error. Source leases prevent concurrent
workers; stale running history is marked interrupted when a later worker claims
an expired lease. SQLite uses a process-local writer lock/BEGIN IMMEDIATE;
PostgreSQL uses transaction advisory lock `7142301`.

## Full run, scheduling and discovery

[sync_all.py](../../collectors/sync_all.py) interleaves enabled source providers,
uses three workers by default, applies per-provider concurrency limits, isolates
source exceptions and records `IngestionRun`. It performs deadline maintenance
after sources, then records aggregate success/partial/failure. The CLI exits
nonzero for partial or failed full runs and writes a detailed JSON artifact.

Base HTTP requests make at most four attempts for transport errors and selected
429/5xx responses, honor bounded Retry-After, add backoff/jitter and track request
costs. Most other HTTP status failures stop immediately. This is not a universal
circuit breaker on every provider; source cooldown and provider-specific detail
circuits cover different failure levels.

Discovery stages live in candidate JSON: discovered, provider_detected, verified,
rejected, temporarily_unavailable, plus unsupported_provider for detection only.
`discover_batch` checkpoints atomically and skips verified rows; `--retry` retries
unsuccessful rows but unsupported platforms stay deferred. There is no database
Candidate model or automatic candidate activation. Use reviewed output to update
the trusted source registry, then register/seed explicitly. See [adding a provider](adding-a-provider.md).
