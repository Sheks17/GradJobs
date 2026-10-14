# Neon egress optimization

14 October 2026. The account owner measured 0.32 GB storage, 1.57 CU-hours and
5.58 GB outbound transfer since 12 October. Production connections are currently
quota-blocked. No production data was downloaded, deleted or reset for this work.

## Diagnosis

`sync_source` previously selected every job column for change comparison, including
descriptions and raw provider JSON. Lifecycle reconciliation selected full active
rows again. Workday additionally loaded its full detail cache from Neon. Changed
postings and deduplication checks also fetched full ORM entities. `/jobs` loaded
full rows even though its response excludes descriptions/raw data; `/jobs/{id}`
loaded private raw payloads that its response does not expose.

These were ORM expanded-column reads, even where SQL did not literally use `*`.
Aggregated statistics and company queries already returned compact values and
remain aggregates. Search still evaluates descriptions within PostgreSQL; it does
not transfer them to the API just to filter or rank results.

## Implementation

- A nullable 64-character `ingestion_fingerprint` stores a canonical SHA-256 of
  normalized source content, including descriptions, raw data and metadata.
  Matching version and active-state eligibility are checked inside SQL.
- Each source loads four compact columns: source posting ID, eligible fingerprint,
  preserved posting date and closing date. Unchanged observations update in
  batches of 500, scoped by source, without returning job entities.
- Existing rows initialize hashes by comparing incoming content inside the
  database. Only the update status is returned. No full-row download, forced
  reclassification or posting `updated_at` change occurs for an unchanged legacy
  row. Incoming comparison parameters are database ingress, not outbound job data.
- Changed/new upserts load only required identity/deadline fields. Duplicate
  candidates return ID/location/application URL/provider, not body/raw JSON.
  ORM writes may return small generated timestamp/identity values, never full jobs.
- Lifecycle queries select only lifecycle fields, exclude seen postings in SQL,
  and promote surviving aliases using identities/pointers only. Closure rules,
  source isolation, deduplication and matching rules remain unchanged.
- List/detail APIs explicitly select their existing public schema fields with
  deferred-field raises enabled. Lists exclude descriptions and raw data; details
  include the requested description but exclude raw data and internal fields.
  Response fields and search/ranking behavior are preserved.
- Workday's disposable gzip detail cache moves to ignored local files restored
  through GitHub Actions cache. It contains public postings only. The same
  six-hour TTL, summary checks and bounded detail requests apply. Valid cached
  details are saved even after a partial ingestion. Cache absence/corruption causes
  public employer requests, never a Neon raw-data download. GradJobs-only cache
  timestamps do not masquerade as posting changes; real source content stays hashed.

Migration `c53e0a2026` adds one nullable column to existing jobs. It does not delete
or rewrite production rows. No matching files or thresholds were changed. Ingestion
cadence remains minutes 7 and 37 UTC; there was no silent freshness tradeoff.

## Measured row-payload estimates

The read-only `python -m collectors.measure_egress` command inspected the existing
local **13,895-real-posting snapshot** (Greenhouse, Lever, Ashby, SmartRecruiters,
USAJOBS). It did not connect to Neon. Estimates count UTF-8 text values plus
PostgreSQL-style DataRow framing; SQLite/JSONB representations differ slightly.
Values are decimal MB/KB. This is not a billed-byte or live wire measurement.

| Path | Before | After | Estimated reduction |
| --- | ---: | ---: | ---: |
| Unchanged sync: job state + lifecycle reads | 584.161 MB | 1.829 MB | 99.69% |
| Twelve representative U.S. job-list rows | 403.544 KB | 14.572 KB | 96.39% |
| Same twelve detail rows | 403.544 KB | 120.367 KB | 70.17% |

Before, the source comparison read accounted for 296.176 MB and lifecycle reread
for 287.985 MB. The snapshot contains no Workday jobs, so it excludes the additional
Workday raw-cache savings. The old baseline also omits additional full-row reads
for changed upserts/deduplication. Roughly ten such full scans could account for
about 5.84 GB, consistent with the observed order of magnitude, not proof of the
exact billing attribution.

At 48 triggers/day for 30 days, core unchanged-row reads for this snapshot fall
from approximately **841.2 GB to 2.63 GB**. Scaling the compact state estimate to
the previously audited 16,581 production rows gives about **2.18 MB/run or 3.14
GB/month**. These extrapolations exclude source/history control queries, updates,
missing/expired jobs, migrations, API traffic and TLS/protocol overhead; observed
GitHub timer delivery was less frequent than configured triggers. They are not a
guarantee that total usage stays under the Free allowance.

Neon documents [5 GB of outbound transfer on Free and warns about ORM
over-fetching](https://neon.com/blog/how-to-make-the-most-of-neons-free-plan).
Actual billable savings and remaining monthly headroom must be checked after
database access returns. Query projection cannot refund already consumed egress
or remove an existing quota lock.

## Verification and rollout

Tests assert SQL SELECT projections, no description/raw-data reads on unchanged
syncs, server-side legacy initialization, preserved update/posting timestamps,
raw-content change detection, JSON key-order stability, cache corruption handling
and existing API/lifecycle behavior. PostgreSQL CI checks JSONB comparisons and
the additive migration; SQLite remains the local fallback. Final test counts and
deployment status are recorded after release verification.

Before production ingestion, run the additive Alembic migration after quota access
is restored. The first Workday cache is cold and may fetch employer details;
subsequent valid-cache runs use the existing TTL. Measure Neon's network counter
before/after a single run and ordinary API usage, then extrapolate using actual
run frequency and row growth. No production reset, secret transfer or paid plan
change is needed to validate the code changes locally.
