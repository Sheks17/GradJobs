# GradJobs MVP completion report

Updated 14 October 2026. The timer blocker was cleared by three successful
automatic scheduled runs on 13 October. The latest refreshed all 84 sources.
Today Neon rejects connections because the account/project quota is exceeded.
**GradJobs MVP is not currently operationally complete:** restore Neon access and
verify the new cloud import and production smoke checks. No new development phase
is required. See [final ATS expansion](final-ats-expansion.md) for 102 verified
employers, nine collectors and current validation. The detailed 12 October
measurements below remain historical observations, not current counts. Final
expansion CI passed 338 backend, 13 frontend and nine browser tests. New-provider
isolated imports created 133 postings across 15 verified employer sources;
production writes and current active counts remain blocked by the database quota.

## Production and scale

- [Repository](https://github.com/Sheks17/GradJobs)
- [Application](https://gradjobs-drab.vercel.app)
- [API health](https://gradjobs-drab.vercel.app/api/health); API prefix `/api`.
- **87 verified employers:** 83 enabled, four additional verified Workday
  candidates disabled. One federal query source is counted separately.
- **84 enabled sources**, 83 healthy and one partial Autodesk source.
- **16,578 active canonical jobs**, all countries; **9,286 active U.S. jobs**.
  These counts include all active roles, not just early-career recommendations.
- PostgreSQL audit at **10:51:37 UTC**: 16,581 stored jobs, 27,120 location rows,
  258 source-sync records, four ingestion runs; revision **b42f0c2026**.

| Provider | Enabled sources | Active canonical jobs, all countries |
| --- | ---: | ---: |
| Greenhouse | 38 | 8,334 |
| Lever | 9 | 2,344 |
| Ashby | 25 | 2,420 |
| SmartRecruiters | 5 | 1,061 |
| USAJOBS | 1 | 382 |
| Workday | 6 | 2,037 |
| **Total** | **84** | **16,578** |

Counts came from production after the latest full ingestion. `/api/stats` is
U.S.-scoped; `/api/stats/providers` includes all countries and excludes duplicate
aliases. Current values are available there and at `/api/sources`.

## Workday and employer coverage

Ten employers passed full reported pagination, details and normalization:
Adobe, Autodesk, Intel, Leidos, Illumina, MillerKnoll, Wells Fargo, Guidewire,
Zendesk and Workday. Adobe, Autodesk, Intel, Guidewire, Zendesk and Workday are
enabled in production; the other four remain verified candidates. See
[employer-level verification](phase4b-workday-verification.md).

Fresh repeat pagination confirmed unique IDs and stable application links for
common postings. Intel added one ID and lost one. Four Wells Fargo postings lacked
location metadata; unknown values stay unknown. Leidos reported 2,000 postings;
verification covers the reported snapshot, not complete global employer coverage.
NVIDIA, Cisco, HPE and Cadence did not pass full validation; Qualcomm did not pass
discovery. No challenges or access restrictions were bypassed.

The enabled registry grew from 65 employers plus one federal source to 83 employers
plus one federal source. Twelve technology employers and six Workday boards were
added after verification. The 200–300 target was not reached; it is not a quota.
Empty, malformed and unverified sources were excluded. Resumable batch discovery
preserves candidate stages without automatically enabling unverified sources.
Four verified disabled configurations are committed separately from the registry.

## Database, hosting and ingestion

Next.js/React/Tailwind and FastAPI are separate services in the existing Vercel
project. Browser requests use same-origin `/api`; GitHub Actions performs long
ingestion into persistent Neon PostgreSQL. The local computer is not needed.
See the [architecture diagram](../README.md#problem-and-architecture),
[deployment operations](deployment.md) and [engineering decisions](design-decisions.md).

The additive Alembic migration and repeated production maintenance succeeded.
Read-only PostgreSQL audits verified revision, indexes, JSONB columns and counts.
Production search/filter requests exercised the actual database. PostgreSQL CI
validated upgrade and `alembic check` without schema drift. Production was never
reset; a downloadable production backup was not available or claimed.

Cadence is **twice hourly at minutes 7 and 37 UTC**, on default `main`.
`INGESTION_ENABLED=true` and repository secret names were verified. Production
validation rejects SQLite/missing database configuration. Ingestion and
maintenance share a concurrency group, manual dispatch works, result artifacts
are retained and partial runs exit unsuccessfully. Timer delivery is best effort;
[GitHub documents scheduling delays](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

| Check | Observed result |
| --- | --- |
| Workday recovery | Six of six sources successful; completed **10:32:25 UTC**; 2,035 fetched, 666 created, 348 updated, 1,021 unchanged; 896.660 seconds |
| Latest full run | Completed **10:43:32 UTC**; 83 successful, one partial, zero failed/zero skipped sources; **629.123 seconds** |
| Full-run writes | 16,590 fetched; 1,038 created; 2,041 updated; 13,488 unchanged; 22 intentionally skipped; one invalid posting; three closed |
| Latest successful source update | **10:43:32 UTC**; not a claim of an entirely successful full run |
| Final database maintenance | Successful production migration/seed/read-only audit; no ingestion requested |
| Timer event | Enabled/configured; no actual `schedule` event observed yet |

Autodesk later returned a summary without an application path. Valid postings
were processed, the source became partial, and closure reconciliation was skipped.
A fresh diagnostic confirmed an invalid-path summary. IDs/links were not invented.
The read-only `/admin/ingestion` page shows scope, history, durations, source health
and daily write counts. Provider failure does not stop other employers.

HTTP/database retries are bounded. Workday uses two detail workers, a six-hour
persisted detail cache and a five-consecutive-failure circuit breaker. Source
cooldowns flag repeated failures for review without deleting sources. Batches
commit every 100 rows and renew leases; earlier validated writes survive later
failures. Only repeated complete snapshots can close missing postings; partial
snapshots cannot. Explicit closing deadlines are handled separately.

## Matching and independent holdout

Matching **version 3.0.0 and cutoff 50 remain frozen**. Reviewed 220-posting sample:
**100% precision, 98.7% recall, 99.4% F1, 99.1% four-class accuracy, zero false
positives, one false negative**. These describe that sample, not universal or
new-provider accuracy.

`data/evaluation/final_holdout_review.csv` and companion JSON contain **150 real
production postings**, **25 per provider**, with blank human labels. Earlier sample
IDs, URLs and normalized title/description fingerprints were excluded. Seed
20261012 samples within a bounded company-sorted pool; it is provider balanced,
not prevalence weighted. Predictions are informational; no holdout tuning occurred.
Review files remain ignored local artifacts. Human labeling does not block MVP.

## Testing and production smoke

| Check | Result |
| --- | --- |
| Backend unit/integration/collector fixtures | **305 passed, 11 skipped**, locally and PostgreSQL CI |
| Frontend unit tests | **13 passed**, three files |
| Browser regression | **8 passed**, Linux Playwright CI |
| Optional live-provider suite, separate | **11 passed**, nine fixture cases deselected in that invocation |
| Workday live checks, separate | Ten full snapshots, ten repeat checks; six production source imports |
| Lint/format/types | Ruff, Ruff format, ESLint, Prettier and TypeScript passed |
| Production frontend build | Passed locally, in CI and on Vercel |
| Alembic | SQLite upgrade/downgrade fixtures, PostgreSQL CI upgrade/check and production upgrade/audit passed |

Three existing warnings remain: Starlette/httpx deprecation and two SQLite
expression-index reflection warnings. Local Windows Playwright could not launch;
Linux CI passed and the actual production browser was tested independently.

Public smoke covered homepage, jobs API, search, filters, details, original apply
link, metadata, sources, provider health, ingestion history and saved-search
save/load/delete. A real Workday application page loaded; no application was
submitted. Desktop and 390-pixel layouts had no horizontal overflow. Browser
warning/error logs were empty. Cloud writes were confirmed by subsequent database
audit; saved searches and application tracking write only to browser storage.

## Performance

Three unauthenticated requests per route after expansion, against 16,581 stored
rows. Medians include network/serverless behavior, not a concurrency load test.

| Request | Median milliseconds |
| --- | ---: |
| Default dashboard jobs including seven-day freshness | 102.7 |
| Text search (`software`) | 146.6 |
| Skill filter (`python`) | 119.3 |
| Freshness | 90.4 |
| Provider filter (`greenhouse`) | 102.1 |
| Homepage HTTP response | 59.6 |

First health request: 2,154.3 ms; later requests around 80 ms. Browser navigation to
populated results was approximately six seconds including automation overhead,
not a Web Vitals measurement. Individual source-ID filtering is not exposed;
the measured source selection is the supported provider filter. Existing SQL
search/PostgreSQL were sufficient at measured scale; no external search added.

## Security review

No findings in **198 publication files, 250 Git-history text objects and 26 built
JavaScript bundles** scanned for known local secrets and credential patterns.
This bounded scan is not proof against every possible secret format. `.env`, local
databases/backups, credentials, deployment state, personal interview documents and
reviewer/evaluation files are excluded from Git and uploads. No secrets printed or
committed.

Production source creation/update and source/full sync mutations returned **403**.
Public admin pages expose read-only aggregate health/history. Canonical CORS
preflight succeeded; unexpected origins and localhost were rejected. Invalid
pagination/query length/provider/score inputs returned **422**. SQL parameters are
bound and job text is escaped. Federal ingestion succeeded using Actions secrets;
database/federal credentials are absent from frontend configuration. No anti-bot
bypass or LinkedIn/Indeed scraping was implemented.

## Known limitations and optional future work

Workday support covers observed public CXS tenant sites, not every custom domain
or restricted portal. Description-only changes may lag the six-hour cache.
Date-only fields use UTC midnight rather than invented exact times. Salary parsing
is conservative and supports explicit USD ranges; missing metadata stays unknown.
Frozen rules may miss unusual federal supervisory wording or “3 or more years”;
employer requirements always need review. New-provider holdout labels are pending.

Saved searches/tracking remain local to one browser; cross-device sync and
email/push are not implemented. Production admin mutations are intentionally
disabled. GitHub scheduling has no strict freshness SLA; cancelled worker history
may need operational review after lease expiry. These are documented limitations,
not extra required phases.

Optional: human holdout review, broader verified employer coverage, additional
metadata adapters, cross-device accounts and email alerts.

## Concrete completion blocker

Automatic event delivery was verified in scheduled run **38439471093**, completed
13 October at **17:56:49 UTC**, with 84/84 successful sources and persisted writes.
Today restore database access in Vercel → Storage → connected Neon project →
Usage/Billing, then verify cloud ingestion and production API/job search. No
credentials should be pasted into chat or committed. New-provider production
counts cannot be reported until database access and cloud ingestion succeed.

**GradJobs MVP is not yet complete.** Production is blocked by Neon quota;
automatic scheduled ingestion has been verified.
