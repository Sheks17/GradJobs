# API reference

[Guide index](README.md) · [Read routes](../../services/api/app/api/routes.py) ·
[Source routes](../../services/api/app/api/sources.py)

Paths here are relative to the inner FastAPI app. Local base:
`http://localhost:8000`. Production base: `https://gradjobs-drab.vercel.app/api`.
Thus `GET /jobs` becomes `GET /api/jobs` publicly. UUIDs in URLs are GradJobs IDs.

## Read endpoints

| Method / path | Function | Result and important behavior |
| --- | --- | --- |
| `GET /health` | `routes.health` | Executes `SELECT 1`; 200 DB OK or 503 unavailable |
| `GET /jobs` | `routes.jobs` | `JobPage`: items, total, page, page_size, total_pages |
| `GET /jobs/{job_id}` | `routes.job_detail` | `JobDetail`; 404 unknown UUID, 422 malformed UUID; can return a retained closed job or alias |
| `GET /companies` | `routes.companies` | Company slug/name and counts over visible U.S. jobs, not current dashboard filters |
| `GET /sources` | `routes.sources` | Source configuration/health; limit default 500, range 1–1000; offset ≥0 |
| `GET /sources/{source_id}` | `sources.source_detail` | One source or 404 |
| `GET /sources/{source_id}/history` | `sources.source_history` | Recent attempts; limit default 30, range 1–100; offset ≥0 |
| `GET /stats` | `routes.stats` | All-visible U.S. aggregates, not the filtered results total |
| `GET /stats/providers` | `routes.provider_stats` | Implemented-provider source health, canonical active job counts, latest-attempt costs |
| `GET /stats/ats` | `routes.ats_capabilities` | Full capability registry; unavailable database counts become null |
| `GET /metadata` | `routes.metadata` | Supported role-family names and canonical skills |
| `GET /ingestion` | `routes.ingestion` | Run history, source health and UTC today creation/update counters; limit default 20, range 1–100 |

The inner FastAPI app also has its default generated `/docs`, `/redoc` and
`/openapi.json`; under the production mount these are `/api/docs`, etc. The outer
wrapper disables its own docs only. Generated documentation is not authentication.

## Job filters

The authoritative model is
[JobFilters](../../services/api/app/schemas/jobs.py). See [search](search.md) for
how combinations are interpreted.

| Parameter | Default / bounds or accepted values |
| --- | --- |
| `q` | Optional text, ≤200 characters; first 12 whitespace tokens used |
| `provider` | One of the nine `CollectorProvider` literals |
| `country` | `US`; two uppercase letters or `all` |
| `state`, `company` | Optional strings, ≤100 / ≤300 characters |
| `role_family`, `seniority` | Role string ≤100; seniority literal from shared constants |
| `role_group` | `software`, `support`, `cloud` |
| `skill` | Canonicalized vocabulary skill; unknown skill rejected |
| `remote_type` | Shared remote-type literal: remote/hybrid/onsite/unknown |
| `experience_category` | `no_experience_required`, `0_1`, `0_2`, `1_2`, `1_3`, `2_3`, `3_plus`, `4_plus`, `5_plus`, `unspecified`, `ambiguous` |
| `max_experience` | 3, range 0–40; optional at model level |
| `include_unknown_experience` | true |
| `include_senior`, `include_demo` | false |
| `min_early_career_score` | 50, range 0–100 |
| `min_salary` | Optional nonnegative annual USD minimum |
| `posted_after`, `fresh_after` | Optional timezone-aware timestamps |
| `sort` | `best_match`, `relevance`, `newest`, `newest_posted`, `recently_discovered`, `early_career_score`, `company`, `salary` |
| `page`, `page_size` | 1 / 20; page 1–10000, size 1–100; dashboard sends 12 |

Example local request (the date is illustrative; use a current timestamp):

```text
GET /jobs?skill=React&remote_type=remote&fresh_after=2026-10-08T00%3A00%3A00Z&page_size=12
```

`JobSummary` contains display fields, skills and scoring/conflict evidence, but
no description or raw JSON. `JobDetail` adds description, provenance, extracted
experience evidence and remote restrictions. `is_new` is computed from
`first_seen_at` and `NEW_JOB_HOURS`, not stored as a permanent label.

## Development-only mutations

All require `APP_ENV=development` **and** `ENABLE_ADMIN_API=true`.

| Method / path | Input / purpose |
| --- | --- |
| `POST /sources` | `SourceCreate`: company_name, provider, board_token, optional careers_url, enabled, provider_config; verifies complete nonempty source; 201 created, 409 existing, 422 verification/input failure |
| `PATCH /sources/{source_id}` | `SourcePatch`: company_name, careers_url, enabled, provider_config; unknown fields forbidden |
| `POST /sources/{source_id}/sync` | Sync registered source; 409 busy/disabled; long synchronous development operation |
| `POST /sync` | Full synchronous development sync |

Production forces administration off, so these return 403. There are no account,
saved-search, application-tracking, email or resume-upload endpoints. Do not build
a frontend integration around an endpoint that appears only in an example plan.

## Error interpretation

422 usually means request validation; inspect the response's `detail` fields.
404 means a resource was not found, not a database outage. Health's 503 indicates
database access failure. Other DB-dependent routes do not uniformly map every
database exception to 503; server errors require logs. A list with zero items is
a valid result after filtering and is not proof ingestion failed.
