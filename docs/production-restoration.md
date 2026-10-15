# Production database restoration

Measured 14 October 2026, after the account owner restored Neon access.

## Schema and serving

[Production maintenance run 38655351589](https://github.com/Sheks17/GradJobs/actions/runs/38655351589)
succeeded. Alembic reached `c53e0a2026`, the additive nullable ingestion fingerprint
column. No database reset, deletion, provider migration or matching change was
performed. The audit at 23:39:27 UTC counted 17,085 stored postings, 16,849 active
canonical postings across all countries, 99 sources, 594 source-sync records and
27,950 location rows. These are pre-recovery-run counts.

The public health endpoint returned 200 with database status OK. Homepage,
job list, software text search, Python skill filter, Greenhouse provider filter,
remote filter, API and HTML job details, and `/admin/ingestion` returned 200.
Single-request HTTP timings ranged from 92 ms for job-detail API to 1.19 seconds
for text search, including client/network time; these are smoke observations,
not a load-test percentile or Web Vitals measurement. The 12-result list response
was 63,975 bytes, with no description/raw-data fields. Response sizes vary with
public scoring evidence and provider metadata.

Public sync mutation remained disabled (403), invalid pagination/score returned
422, and an unexpected CORS origin was rejected (400).

## Recovery ingestion

[Full recovery run 38655466612](https://github.com/Sheks17/GradJobs/actions/runs/38655466612)
uses existing repository secrets and the persistent production database. Its
configured schedule remains minutes 7 and 37 UTC, with shared concurrency control.
The run succeeded for **99/99 sources**, with zero failed, partial or busy/skipped
sources. It fetched **16,792 postings**, created **664**, updated **3,565**, observed
**12,539 unchanged**, and skipped 24 job rows. There were zero job failures.
Source reconciliation closed 51 postings and deadline maintenance expired 100;
these are separate counters, not a deduplicated combined closure total.

The ingestion record `5c3a0ffa-3a43-496e-9f81-2a9dce5ab766` ran from
14 October **23:40:24 UTC** to 15 October **00:17:06 UTC** (14 October evening
America/Chicago). Collector duration was 2,201.799 seconds; the complete workflow
including setup took 37 minutes 10 seconds. First-run initialization and actual
posting changes make this unsuitable as a warmed unchanged-run benchmark.

The Workday cache save succeeded: GitHub recorded a **3,811,205-byte** public-detail
cache. The subsequent automatic `schedule` event,
[run 38657855327](https://github.com/Sheks17/GradJobs/actions/runs/38657855327),
started after recovery and successfully restored that cache. Its complete run
result was still pending at this report's cutoff; it is not claimed as another
completed scheduled success. Prior automatic successful runs remain documented.

Fresh production aggregates at approximately **00:19 UTC on 15 October** reported
**17,355 active canonical jobs across all countries**, including **9,662 U.S.
jobs**. The next serialized scheduled run was already active, so these are a
point-in-time aggregate rather than an immutable recovery-run snapshot.

| Provider | Verified enabled employers | Active canonical jobs |
| --- | ---: | ---: |
| Greenhouse | 38 | 8,692 |
| Lever | 9 | 2,384 |
| Ashby | 25 | 2,511 |
| SmartRecruiters | 5 | 1,113 |
| USAJOBS | Federal query source | 342 |
| Workday | 6 | 2,180 |
| Workable | 5 | 19 |
| Recruitee | 6 | 87 |
| BreezyHR | 4 | 27 |
| Total | 98 employers + 1 federal source | 17,355 |

Four additional Workday employers remain verified but disabled candidates,
bringing reviewed verified employer coverage to **102**. All 15 newly added
Workable/Recruitee/BreezyHR employers now have production imports (133 postings
in this aggregate). The restored browser dashboard rendered real results,
matching evidence, application links and pagination; its then-current default
seven-day selection showed 74 recommendations, not the all-active-job total.

## Completion status

**GradJobs MVP is complete.** The quota recovery, additive production migration,
cloud import, public serving and cache-persistence checks clear the concrete
operational blocker. Current release validation remains 346 backend tests,
13 frontend tests and nine browser tests, plus PostgreSQL migration/drift checks,
lint, formatting, TypeScript and builds. This restoration changed documentation,
not application or matching code, so the code validation was not needlessly rerun.
The independent holdout remains unlabeled and the known limitations remain in
the MVP and ATS reports. Billing monitoring is ongoing operations, not a new
required development phase.

## Egress measurement limits

The migration and public API checks are live production observations. The payload
reduction figures in [the egress report](egress-optimization.md) remain estimates
from a read-only local sample, not Neon billing measurements. No billing counter
is exposed through these application/workflow checks. Already consumed transfer
is not refunded by the changes. First-run fingerprint initialization and a cold
Workday cache differ from a warmed, unchanged run; compare the Neon transfer
counter over completed later runs before drawing a billable-usage conclusion.
