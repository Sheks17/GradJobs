# Provider configuration and verification

All providers feed `NormalizedJob` into the same scoring, upsert, location/skill indexing, deduplication, and lifecycle pipeline. Matching version 3.0.0 and the cutoff of 50 are unchanged. Each source keeps its provider, stable board/query identifier, employer name, enabled state, and public `provider_config` JSON. Credentials belong only in environment variables. The source registry preserves existing settings during seed imports.

| Provider | Required identifier | Authentication | Configuration | Capabilities / limitations |
| --- | --- | --- | --- | --- |
| Greenhouse | Observed board token | None for public Job Board API | Empty JSON | Complete public list with descriptions. `updated_at` is not publication time. Salary often absent. |
| Lever | Observed posting site token | None for public Postings API | Empty JSON | Paginated public postings, descriptions, location/workplace and compensation when supplied. |
| Ashby | Observed job-board slug | None for public Posting API | Empty JSON | Public list, full descriptions, multiple locations, publication and compensation when supplied. Unlisted jobs excluded. |
| SmartRecruiters | Case-sensitive company identifier observed in career URL | None for public company Posting API | `country`, `max_pages` | Offset pagination plus per-posting detail requests. Preserves list and detail payloads. Remote/hybrid booleans and released date mapped. Detail failures make the snapshot partial; missing-job closure is skipped. Salary is retained in raw payload when supplied but is not currently normalized. |
| USAJOBS | Stable local search-source identifier, e.g. `technology` | `USAJOBS_API_KEY`, `USAJOBS_USER_AGENT` (registered email) | `queries`, `results_per_page`, `max_pages` | Official Search API with `Fields=Full`. Queries must be scoped by keyword, occupational series or organization. Duplicate results across queries collapse by matched external ID. Federal metadata does not alter legal eligibility assumptions or scores. |
| Workday | Hostname and site token derived from an observed careers URL | None for accessible public CXS endpoints | `careers_url`, `hostname`, `tenant`, `site`, `locale`, `max_pages` | Paginated summaries plus bounded detail retrieval/cache. Descriptions, stable IDs, dates, locations and explicit salary. Blocked/incomplete boards stay candidates. |

SmartRecruiters uses the documented [company Posting API](https://developers.smartrecruiters.com/docs/posting-api). USAJOBS uses the official [Search API](https://developer.usajobs.gov/api-reference/get-api-search) and [authentication headers](https://developer.usajobs.gov/tutorials/search-jobs): Host, User-Agent, and Authorization-Key. No LinkedIn or Indeed scraping is used.

## Controlled source registration

`data/sources.json` is the verified enabled registry. `data/sources/candidates.json` records observed/checked candidates and verification outcomes; candidates are never automatically enabled. Unknown discovery remains unknown. Identifiers are verified through their public endpoints, not derived from employer names. SmartRecruiters discovery recognizes careers and posting URLs.

```powershell
python -m collectors.discover https://careers.smartrecruiters.com/BoschGroup
python -m collectors.verify_sources --provider smartrecruiters --output artifacts/verification.json
python -m collectors.verify_sources data/sources/candidates.json --output artifacts/verified.json
python -m collectors.seed_sources --file artifacts/verified.json
python -m collectors.sync_all --provider smartrecruiters --dry-run --output artifacts/dry-run.json
python -m collectors.sync_all --provider smartrecruiters --output artifacts/live-sync.json
python -m collectors.sync_all --provider usajobs
```

Verification fetches and normalizes without job writes or source/lifecycle mutations. Dry runs additionally execute the existing classifier; `jobs_validated` means validated postings, not database updates. `created`/`updated`/`unchanged` remain zero in dry runs. Fetching still uses public requests and respects backoff. Explicit JSON verification output is separate from the live registry.

USAJOBS searches are seed configuration, not collector code. The pilot uses eight category-scoped searches: Information Technology, Computer Science, Software, Information Systems, Cybersecurity, IT Specialist, Computer Engineer, and Data. Search pagination must complete; reaching the page cap fails the snapshot safely rather than closing unseen jobs. Overlapping searches do not create repeated rows within the source.

## Network safety and observability

`COLLECTOR_TIMEOUT_SECONDS=30`, `COLLECTOR_REQUEST_INTERVAL=0.5`, and `COLLECTOR_MAX_CONCURRENCY=3` configure bounded collection. `COLLECTOR_PROVIDER_CONCURRENCY={"smartrecruiters":2,"usajobs":1}` limits simultaneous sources for specific providers. Source queues are interleaved across providers; capacity-aware submission skips providers at their limit so waiting sources never occupy worker threads; each worker uses its own HTTP client and database session. Network fetches occur outside database write locks. SQLite workers queue in-process before entering the database busy timeout; PostgreSQL retains advisory write locking. Active alias promotion uses a selective set query rather than scanning every closed posting for each employer. SQLite planner refresh samples up to 1,000 index entries and restores the connection setting afterward. See [SQLite analysis-limit documentation](https://www.sqlite.org/pragma.html#pragma_analysis_limit).

Transient transport failures and HTTP 429/500/502/503/504 have a four-attempt budget with exponential backoff and jitter. Permanent 4xx responses are not retried. Numeric and HTTP-date Retry-After values are respected. A delay over 120 seconds ends that attempt safely rather than sleeping past the configured local request budget or retrying sooner than requested. Per-source request spacing is enforced; provider limits are per process, not a distributed quota. Avoid starting multiple schedulers.

`GET /stats/providers` exposes configured/enabled sources, healthy/failing sources, active canonical jobs, latest per-source attempt counts, request latency, failures/rate limits, upsert time, latest successful sync and recent errors. Older history has zero request instrumentation; a zero request count yields unknown latency. Active counts span all countries and exclude duplicate aliases. The Sources page includes a small provider summary. A full-run failure means all attempted sources failed; mixed outcomes are reported as partial success. Individual posting failures use savepoints and skip missing-job reconciliation.

## Federal metadata and deadlines

The normalizer retains organization, department, locations, salary period, qualifications, requirements, hiring paths, security-clearance wording, citizenship evidence, veterans-preference wording, and original JSON. Explicit `graduates`/`student` hiring paths and Pathways/internship wording remain distinguishable. An explicit graduate hiring path is rendered as a graduate-program description signal consumed by the existing engine; no experience years or entry-level title are invented.

Only explicit mandatory citizenship wording creates `requires_us_citizenship=true`. Public trust remains separate from classified security clearance. RemoteIndicator is mapped independently of telework eligibility; telework is not silently treated as remote. Provider-derived remote restrictions exclude application instructions so closing-deadline timezone wording is not presented as a working-hours requirement. These validated fields override generic description inference for USAJOBS. Missing metadata stays unknown. Federal grade-equivalent specialized experience can differ substantially from new-graduate experience; the pilot needs independent human validation before any new scoring assumption.

Source-supplied closing dates are stored as `closing_at`, shown on cards/details, and retained after expiration. Date-only deadlines use inclusive end-of-day UTC; naive API timestamps are represented in UTC with the original value preserved in provider metadata. This is a timezone assumption, not employer-supplied timezone evidence. Expired jobs are marked inactive and excluded from active results, never deleted. A later missing deadline cannot resurrect a known expired job. A genuinely extended future deadline can reopen it through normal upsert behavior.

## Tests and pilot validation

Normal tests use saved real public fixtures and mocked HTTP. Optional live checks must be enabled explicitly; credentials are required only for live USAJOBS checks. Run `python -m pytest -q` for offline coverage. A fresh provider-balanced evaluation sample is produced with `python -m matching.sample_pilot`, excluding every Phase 3 sample ID and leaving all human labels blank. Evaluate it with an explicit review file: `python -m matching.evaluate --input data/evaluation/phase4-pilot.json --reviews data/evaluation/phase4-pilot.csv`.

Measured earlier employer examples are recorded in [Phase 4A verification](phase4a-provider-expansion.md). Workday is implemented in the MVP sprint; current verified coverage and limitations are recorded in [MVP completion](mvp-completion.md). iCIMS, Jobvite, BambooHR and custom-site ingestion remain optional future adapters.

## Workday and batch discovery

Workday sources use `provider_config` with observed `careers_url`, `hostname`, `tenant`, `site` and `locale`. Hostname shards and site names are retained; identifiers are never derived from employer names. Only HTTPS employer `*.wdN.myworkdayjobs.com` hosts are accepted. The board token includes the hostname and site. Public CXS summary pages and detail responses provide stable posting IDs and exact dates where present; missing dates remain unknown. Date-only Workday start/end dates are represented at midnight UTC, an explicit timezone assumption. Each source allows two concurrent detail requests and the provider allows one source at a time by default.

Every sync retrieves listing pages. Unchanged summaries reuse persisted details for `WORKDAY_DETAIL_CACHE_HOURS` (default six, zero disables caching); new/changed summaries retrieve details immediately. A description-only change can remain cached until that interval expires. Five consecutive detail failures open a per-run circuit and stop further pages/details; already in-flight requests may finish. The result remains partial, so closures never follow an outage.

```powershell
python -m collectors.discover https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced
python -m collectors.discover_batch data/sources/workday-candidates.csv --output artifacts/discovery/workday.json
python -m collectors.discover_batch data/sources/workday-candidates.csv --output artifacts/discovery/workday.json --retry
python -m collectors.verify_sources artifacts/candidates.json --output artifacts/verified.json --cache artifacts/verification
python -m collectors.seed_sources --file artifacts/verified.json
python -m collectors.sync_all --provider workday --output artifacts/workday-sync.json
```

Batch discovery writes resumable candidate stages but never enables sources. Discovery validates list access, pagination and one detail; full snapshot verification additionally normalizes every posting. Only full verified records are promoted into the enabled registry. Malformed summaries, missing descriptions, blocked requests or detail failures prevent complete-snapshot closure reconciliation. Real Workday boards return `total: 0` on later pages; pagination uses the first page's count. No anti-bot bypass is implemented. Avoid interpreting a provider-reported limit as complete global employer coverage.

Source failures have a configurable review threshold (`SOURCE_FAILURE_THRESHOLD=3`) and retry cooldown (`SOURCE_COOLDOWN_MINUTES=60`). Sources remain registered and enabled while flagged; they are retried after cooldown. `/api/ingestion` and `/admin/ingestion` expose read-only counters and history. Failed and partial scheduled runs exit nonzero and retain JSON artifacts.

Optional Phase 4 live checks (no job writes):

```powershell
$env:RUN_LIVE_TESTS="1"
python -m pytest tests/test_live_phase4a.py -m live -q
```

Configure both USAJOBS environment variables before the federal check; it otherwise skips. Do not place either value in the source registry or reports.
