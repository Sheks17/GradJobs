# Phase 2 live ingestion verification

Verified October 8, 2026. Measurements below describe two completed local live runs; ongoing collection can change counts. Local preview: http://localhost:3000, API: http://localhost:8000, database: `gradjobs-live.db`. The original `gradjobs-preview.db` demo database was preserved.

## Real source coverage

| Provider   | Verified employers | Stored postings after second run | Live integration examples        |
| ---------- | -----------------: | -------------------------------: | -------------------------------- |
| Greenhouse |                 33 |                            7,433 | Stripe, Cloudflare, Datadog      |
| Lever      |                  7 |                            1,643 | Palantir, Spotify, Veeva Systems |
| Ashby      |                 17 |                            2,251 | Notion, Ramp, Linear             |

All 57 configured boards were fetched, normalized and ingested twice. The nine examples also passed separately opt-in live integration tests. Example identities are test/seed data, not branches in production collector logic. The complete registry includes per-board verification URLs and dates in `data/sources.json`. Captured single-post response fixtures and provenance live under `tests/fixtures/live/`.

**Greenhouse:** Stripe, Cloudflare, Datadog, Discord, Figma, MongoDB, Twilio, Okta, Elastic, Databricks, Robinhood, Coinbase, Duolingo, Affirm, SoFi, Toast, Samsara, Rubrik, Fivetran, Mixpanel, Intercom, Asana, Airbnb, Dropbox, ZoomInfo, GitLab, LaunchDarkly, Smartsheet, Coursera, Pure Storage, Adyen, Brex, Gusto.

**Lever:** Palantir, Spotify, Veeva Systems, Zoox, Wealthfront, Included Health, SEP.

**Ashby:** Notion, Ramp, Linear, Sentry, Supabase, Vanta, Perplexity, OpenAI, Ashby, Benchling, Zip, Cerebras Systems, Nooks, Netic, Sentra, ClickHouse, ElevenLabs.

## Observed sync results

| Metric                | First run | Repeat run |
| --------------------- | --------: | ---------: |
| Sources attempted     |        57 |         57 |
| Sources successful    |        57 |         57 |
| Sources failed        |         0 |          0 |
| Jobs fetched          |    11,336 |     11,335 |
| Created               |    11,325 |          2 |
| Updated               |         0 |          3 |
| Unchanged             |         0 |     11,319 |
| Intentionally skipped |        11 |         11 |
| Posting failures      |         0 |          0 |
| Closed                |         0 |          0 |
| Seconds               |   328.501 |    325.315 |

**11,327 live postings** were stored after the repeat run. All **11,325 original IDs and first_seen_at values remained unchanged**. Two genuinely new provider IDs appeared; three changed payloads updated existing records. Three postings disappeared once and correctly remained active with one missing observation. No source-key duplicates were created; all 11,327 `(source_id, source_job_id)` pairs are unique. There were no cross-source duplicate aliases in this snapshot; promotion and grouping behavior is exercised by deterministic tests.

Both runs produced 114 successful persisted source-history rows and left all 57 sources healthy. Eleven prospect/unlisted records per pass were intentionally excluded. Failed and partial snapshot closure behavior was tested with mocks, not induced against employers.

## Data and UI verification

- 5,668 active canonical U.S.-eligible postings across all experience levels; 28 results in the default U.S., active, technology, score ≥50, up-to-3-years/unknown, non-senior, last-seven-days view.
- 7,031 postings had explicit experience extracted; 2,454 had multiple normalized locations. No stored description was empty.
- Employer publication remains distinct from first discovery and last observation. Unknown publication dates stay null; NEW is based on first discovery. API dates serialize UTC with Z.
- Desktop flow checked search, six-hour/any-time freshness, newest-posted sort, senior toggle, original application link, description, scoring reasons, and persistent application status after reload.
- Mobile flow checked freshness controls and viewport overflow at 390 pixels. The source page displayed healthy boards, accurate counts, timestamps, and persisted history.
- The optimized multi-location filter reduced a measured local stats request from ~6.4 seconds to ~0.37 seconds on this snapshot. This is a local observation, not a production benchmark.

Sample application links fetched successfully (HTTP 200) without submitting applications:

- [Affirm — Software Engineer, Early Career (SF)](https://job-boards.greenhouse.io/affirm/jobs/8010617003): greenhouse, 3,866 description characters, score 85; original source metadata and UTC timestamps verified.
- [Palantir — Data Engineer - Talent Acquisition Operations](https://jobs.lever.co/palantir/1b690123-1766-4e75-a0ef-0f58afa864b4/apply): lever, 7,698 description characters, score 70; original source metadata and UTC timestamps verified.
- [ElevenLabs — Full-Stack Engineer (Back-End Leaning)](https://jobs.ashbyhq.com/elevenlabs/c7d59014-b918-4c15-ae33-79f5c9f2cf9f/application): ashby, 4,716 description characters, score 50; original source metadata and UTC timestamps verified.

Screenshots: ignored local artifacts `artifacts/dashboard-desktop.png`, `artifacts/dashboard-mobile.png`, and `artifacts/sources-desktop.png`. Raw snapshots, run logs, summaries, link/data audit, and repeat identity audit are retained locally under `artifacts/live/`; they are not credentials and are not required in version control.

## Provider issues and exclusions

The initial candidate survey tested 72 board/provider combinations. Eleven returned HTTP errors and four returned valid empty boards; these 15 were excluded from the curated launch seed. This does not imply the companies have no jobs, only that those specific candidate boards were not usable launch sources.

- HTTP errors: Greenhouse candidate tokens hubspot, dbtlabs, amplitude, sentinelone, tenable, nutanix; Lever atlassian, netskope, cision, fullstacklabs; Ashby retool.
- Empty: Lever rackspace; Ashby deel, vercel, mercury.
- Greenhouse publication and structured compensation are not consistently present in list payloads. `updated_at` is never repurposed as publication. Prospect posts are skipped and optional response totals are checked for completeness.
- Lever requires complete pagination; a page failure aborts the snapshot. Ashby can expose secondary addresses and unlisted records. Both now preserve normalized multi-location data.
- All 57 included boards normalized without row failures in both full runs. No credentials, anti-bot bypasses, or application submissions were used.

## Schema, API, and automation

Migration `7bf8b519f9b4` adds source health/lease fields, `source_syncs`, JSON/JSONB `locations`, indexed relational `job_locations`, `missing_since`, and `consecutive_missing_syncs`. Existing closed_at is reused. Full upgrade/downgrade and no-drift checks pass on SQLite; PostgreSQL DDL generation is checked and CI is configured for PostgreSQL.

Added GET source detail/history, verified POST registration, PATCH settings, single-source and all-source POST sync endpoints. Mutation endpoints require development mode plus ENABLE_ADMIN_API=true and remain blocked in production. Production administration will require authentication. The browser source page is read-only.

The local Python scheduler was started after the two verified runs with `--wait-first`, using a 30-minute delay and the live database. Log: `artifacts/live/scheduler.log`. It runs only while this process and machine remain active; it is not installed as an OS startup service. The API itself never starts schedulers.

A cron-compatible CLI and gated GitHub Actions every-30-minute workflow are configured. Remote Actions has not been activated: it needs a provisioned/migrated/seeded production database, secret INGESTION_DATABASE_URL, and variable INGESTION_ENABLED=true. See [operations](ingestion.md) for setup, lease recovery and closure configuration.

## Checks and limitations

- Backend: **135 passed**, nine network tests skipped by default; **nine live tests passed** when explicitly enabled.
- Frontend: **seven unit tests passed**; ESLint, Prettier, TypeScript, and Next.js production build passed.
- Browser: **all three acceptance tests passed together** in the final Edge run (7.2 seconds), including desktop discovery/tracking, mobile overflow/filters, and source history. Earlier attempts had intermittent Edge process exits. No application page errors were observed in the completed desktop run.
- Ruff lint/format and Alembic schema drift checks passed. One upstream Starlette/httpx test-client deprecation warning remains.
- PostgreSQL is not installed locally, so actual PostgreSQL execution and hosted GitHub Actions have not been claimed. SQLite supports the preview with WAL and serialized writes.
- Closure on elapsed production time was not waited out; grace, reappearance, partial failures, lease fencing, and duplicate promotion have deterministic tests. Real jobs with one absence remained active as intended.
- Location/experience/title matching remains heuristic; bare city names, degree alternatives, and incomplete descriptions can produce missed jobs or imperfect scores. No claim of complete U.S. job coverage or personal suitability is made.
- Discovery is bounded public-page inspection; JavaScript-only or restricted sites may remain unknown. Source history retention and production operator authentication remain future work.

Recommended Phase 3: human-labeled matching evaluation, more precise alternative-experience and city-only location handling, saved searches, source-failure alerts, and authenticated application tracking when needed.
