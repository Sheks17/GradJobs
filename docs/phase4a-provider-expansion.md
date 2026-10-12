# Phase 4A provider expansion verification

Measured locally on October 10, 2026 using official/public ATS endpoints and the configured live SQLite database. This report describes a controlled pilot and one completed full run; it does not establish long-term availability or matching accuracy on the new providers.

## Delivered foundation

SmartRecruiters and official authenticated USAJOBS now use the existing normalization, scoring, upsert, deduplication, and lifecycle pipeline. Additive migration `1a4b0c4e2026` adds source `provider_config`, job `closing_at` and `provider_metadata`, and request/upsert metrics on source history. The live migration is at head; SQLite upgrade/downgrade and PostgreSQL offline DDL were tested. No live PostgreSQL integration environment was available.

Provider capabilities and a factory replace orchestration branches. Provider-only sync, no-write dry runs and source verification, transient retry/backoff with Retry-After, bounded global/provider concurrency, and partial-success summaries are available. `GET /stats/providers` reports source and job counts plus latest per-source metrics. Sources shows provider health; advanced filters include provider selection. Federal cards/details display only supported metadata and source deadlines. Expired postings remain retained, inactive, and excluded from active results; surviving source aliases are promoted.

## Verified sources and controlled rollout

The registry grew from **57 to 65 verified employer boards**, plus **one federal search configuration**: 66 enabled source configurations in total. The optional 100â€“150 employer target was not pursued with unverified identifiers. `data/sources/candidates.json` keeps candidates separate; Visa and PublicisGroupe returned empty public snapshots and remain unenabled.

| New employer | Provider identifier | Complete pilot postings |
| --- | --- | --- |
| Bosch Group | SmartRecruiters `BoschGroup` | 354 |
| Nagarro | SmartRecruiters `Nagarro1` | 161 |
| ServiceNow | SmartRecruiters `ServiceNow` | 422 |
| Sopra Steria | SmartRecruiters `SopraSteria1` | 30 |
| Western Digital | SmartRecruiters `WesternDigital` | 92 |
| Airtable | Greenhouse `airtable` | 4 |
| Shield AI | Lever `shieldai` | 616 |
| Replit | Ashby `replit` | 69 |

These are source-scoped snapshot counts, not a claim that all are technology or early-career jobs. SmartRecruiters uses a US country filter. Full detail descriptions, locations, original links and stable identifiers normalized successfully for all five complete snapshots. New employer identifiers appear only in seed/configuration and test/report evidence, not provider logic.

USAJOBS uses eight category-scoped configurable searches: Information Technology/2210, Computer Science/1550, Software/2210, Information Systems/2210, Cybersecurity/2210, IT Specialist/2210, Computer Engineer/0854, and Data/2210. Overlap collapsed to **392 unique postings** in the initial pilot. Credentials remain in the ignored local `.env`; no credential values are in the registry, fixtures or report. A separate registered-source verification fetched/normalized 392 postings with zero normalization failures and no job or health writes.

## Dry run and limited live pilot

SmartRecruiters dry run fetched/normalized **1,059** postings in **717.865 seconds**, with 1,072 requests, 463.58 ms average request latency, and zero failed requests, rate limits or normalization failures. It wrote no jobs or lifecycle changes. Its limited live run created **1059** jobs in **924.919 seconds**, with 1,072 requests, 481.7 ms average latency and 77.741 seconds of measured upserts; all five sources succeeded.

USAJOBS dry run validated **392** postings in **30.804 seconds** with 20 requests and zero writes/errors. Its limited live run created **392** jobs in **150.312 seconds**, with 20 requests, 229.4 ms average latency and 39.534 seconds of upserts. Additional existing-provider pilots created 4 Airtable, 616 Shield AI, and 69 Replit rows after their own dry runs. Before the full refresh, all original 11,739 payloads, source URLs and first-seen values remained unchanged.

## Completed full-sync measurements

The final full run reported **success**, attempted **66** sources, succeeded on **66**, failed on **0**, and partially succeeded on **0**. Wall time: **1181.433 seconds** at configured concurrency 3, with SmartRecruiters limited to two sources and USAJOBS to one.

| Provider | Sources | Fetched | Created | Updated | Unchanged | Errors | Requests | Avg request ms | Upsert seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ashby | 18 | 2307 | 0 | 0 | 2307 | 0 | 18 | 234.22 | 151.613 |
| greenhouse | 34 | 7519 | 0 | 0 | 7508 | 0 | 34 | 293.62 | 524.983 |
| lever | 8 | 2267 | 0 | 0 | 2267 | 0 | 28 | 777.36 | 139.47 |
| smartrecruiters | 5 | 1059 | 0 | 0 | 1059 | 0 | 1072 | 487.06 | 56.599 |
| usajobs | 1 | 392 | 0 | 0 | 392 | 0 | 20 | 400.2 | 38.984 |

Request latency measures HTTP attempts, including failures, but excludes deliberate spacing/backoff and database time. Upsert totals sum per-source normalization/scoring/database loop time; wall time also includes queues, leases, reconciliation and maintenance. Parallel totals should not be summed as wall time. The 11 skipped Greenhouse records are talent-pool prospect posts with no open requisition ID, intentionally excluded by the existing normalizer. Detailed run artifacts are local ignored files under `artifacts/phase4a/`, including `full-sync.json` and each limited pilot summary.

No failed, partial, busy, or disabled sources in the final full run.

## Database and deduplication

Baseline retained/active rows: **11,739 / 11,393**. After the full run: **13,879 / 13,533**. Active canonical counts below exclude aliases and demo jobs and span all countries; the dashboard's US/default relevance filters produce smaller totals.

| Provider | Retained rows | Active rows | Active canonical jobs |
| --- | --- | --- | --- |
| ashby | 2369 | 2307 | 2307 |
| greenhouse | 7768 | 7508 | 7508 |
| lever | 2291 | 2267 | 2267 |
| smartrecruiters | 1059 | 1059 | 1059 |
| usajobs | 392 | 392 | 392 |

The final full sync repeated the new sources through live APIs. All **11,739** original IDs, source identifiers and first-seen timestamps survive unchanged. All **13,879** repeat-baseline rows retain their IDs and discovery dates. There are **0** repeated `(source_id, source_job_id)` groups and **0** retained duplicate aliases. Normal source payload updates during the full refresh are allowed; source records are never deleted. Regression tests cover same-source repeats, company-scoped cross-provider mirrors, preserved source references and promotion after deadline expiry. SQLite quick-check and foreign-key checks are recorded separately in `database-check.json`.

## Source health after the final run

| Provider | Configured | Enabled | Healthy | Failing |
| --- | --- | --- | --- | --- |
| ashby | 18 | 18 | 18 | 0 |
| greenhouse | 34 | 34 | 34 | 0 |
| lever | 8 | 8 | 8 | 0 |
| smartrecruiters | 5 | 5 | 5 | 0 |
| usajobs | 1 | 1 | 1 | 0 |

Healthy means an enabled source has a successful sync and no current error. The provider API aggregates latest attempts per source, rather than pretending those measurements are a single simultaneous provider run. Interrupted/error history remains available even after a successful recovery.

## Errors found and corrections

A federal application-deadline sentence also appeared as a remote timezone restriction in visual QA. USAJOBS now excludes application instructions from remote-work evidence, with a regression that preserves actual working-hours restrictions. The provider-only normalization refresh is recorded in `usajobs-normalization-refresh.json` and `usajobs-normalization-final.json` (including plural Applications wording); it uses the same upsert path and preserves discovery identifiers. A USAJOBS citizenship regex initially stalled on a long qualifications paragraph. Replaced it with bounded explicit phrase matching in the provider normalizer and added a long-text regression; no global matching rule changed. A first full run exposed SQLite worker busy-timeout errors. Workers now queue before SQLite write acquisition; HTTP remains concurrent. A second diagnostic run exposed repeated closed-canonical/alias scans for every source. Promotion now selects only canonical IDs referenced by active aliases; the selective query took 0.036 seconds on the live database. Both diagnostic runs were deliberately interrupted, their histories retained, leases released, and the final run restarted. Failed standalone maintenance probes encountered cross-process write contention and are not used as performance measurements. Only one scheduler should run against the local database.

SQLite planner refresh uses bounded index sampling, following the [SQLite analysis-limit documentation](https://www.sqlite.org/pragma.html#pragma_analysis_limit). No claim of an isolated before/after planner speedup is made. The dominant SmartRecruiters cost remains one detail request per posting plus safe spacing. Capacity-aware submission was added after observing temporary worker starvation in the measured run: jobs are submitted only when their provider has capacity, so waiting sources do not occupy worker threads. A regression holds the slow provider until all fast-provider sources finish. The full timing above includes the earlier semaphore queue behavior; no improved full-run timing is claimed. No detail-request fanout or distributed quota system was introduced.

The initial browser checks found overflowing federal badges and unstable assertions involving locale formatting, changing history button names, pre-hydration controls and sources actively syncing. Badge rows now wrap on mobile. Tests wait for rendered controls/data and inspect a source that is healthy in the displayed snapshot. No UI errors were hidden.

## Validation

- Offline backend suite: **283 passed, 11 optional live tests skipped**. Three existing dependency/index-reflection warnings remain. After selective reconciliation changes, targeted lifecycle/provider coverage was rerun; the full offline suite and targeted normalization coverage passed.
- Optional official endpoint checks: **2 passed** (SmartRecruiters list/detail and authenticated USAJOBS search).
- Frontend unit tests: **11 passed**. ESLint, Prettier, TypeScript and the production Next.js build passed.
- Browser suite: six live scenarios cover filters/classification, application tracking, mobile viewport, source history, provider health, provider filtering and federal details. All six passed in 22.4 seconds; screenshots are under `artifacts/phase4a/`.
- Alembic check reports no new operations; additive migration upgrade/downgrade and offline PostgreSQL DDL tests pass.

## Fresh independent review sample

`data/evaluation/phase4-pilot.json` and `.csv` contain **100** fresh postings: 35 SmartRecruiters, 35 USAJOBS, 10 Greenhouse, 10 Lever and 10 Ashby. All previous 220 sample IDs are excluded. Every human label, reviewer and note remains blank. Sampling is stratified across providers and scores, not prevalence weighted; predictions are stored separately from labels. The maximum sampled description length is 21,340 characters. New-provider matching accuracy remains unmeasured until independent human review.

Matching version **3.0.0**, early-career cutoff **50**, experience/seniority weights, role scoring and confidence logic are unchanged. The previous user-confirmed 220-job validation remains precision 100%, recall 98.7%, F1 99.4% and four-class accuracy 99.1%; those metrics do not generalize automatically to this pilot.

## Limits and Phase 4B readiness

**Ready for a controlled Phase 4B provider pilot.** The final full run succeeded across all 66 sources. SmartRecruiters compensation remains in raw payload rather than normalized salary, details cost additional requests, and only verified public US snapshots were enabled. USAJOBS coverage is limited to configured technology searches; federal grade-equivalent experience and legal eligibility require source review. Telework is not treated as remote. Date-only/naive closing timestamps use documented UTC assumptions while retaining the original source value. Per-process concurrency is not a distributed provider quota, and SQLite writes remain serialized.

Phase 4B should introduce Workday as a separate adapter with observed tenant/site identifiers, independently verified list/detail behavior, captured fixtures, bounded discovery and a small dry-run/live pilot. Review the fresh provider sample before expanding score assumptions. Workday, iCIMS, Jobvite, BambooHR, custom scraping, authentication and AI scoring are not implemented in Phase 4A.

## Final runtime confirmation

The final federal follow-up updated 3 rows, confirmed 389 unchanged, created zero jobs, and had zero failures in 57.917 seconds. A database scan found zero application/closing/deadline sentences remaining in USAJOBS remote timezone evidence. The post-refresh provider browser checks both passed. The final provider regression set passed 23 tests after this wording correction.

API and database health are OK. `/stats/providers` confirms 66 healthy sources and zero failing sources. The local 30-minute scheduler resumed as one parent/child Python instance with `--wait-first`, loading capacity-aware scheduling; the frontend remains available at http://localhost:3000/. Credentials remain ignored.
