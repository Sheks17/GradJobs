# Add an ATS provider safely

[Guide index](README.md) · [Collector architecture](ingestion.md)

This is a maintenance recipe, not a request to expand the completed MVP. Add a
provider only when separately required. Adding one verified employer on an
existing adapter is a much smaller task than implementing an ATS.

## 1. Establish the actual access contract

Find an observed employer careers URL and an allowed public feed or official keyed
API. Inspect the public contract and record evidence in the support matrix and
capability registry. A recruiter/customer API is not automatically available for
anonymous job discovery. Do not use guessed tenants, private endpoints, stolen
keys, challenge bypasses or a public page as proof of feed access.

For an existing adapter, discovery can start with:

```text
python -m collectors.discover <observed-careers-url>
python -m collectors.discover_batch data/sources/candidates.csv --output artifacts/discovery/candidates.json
```

The CSV needs `careers_url`; `company_name` and other public provenance columns
can be retained. Use the actual input filename available in your checkout rather
than assuming the illustrative `candidates.csv` exists. Batch output checkpoints
stages and does not activate sources. Verification and activation are separate.

## 2. Implement the adapter boundary

Create `collectors/<provider>.py` extending `Collector`. Use an observed board ID
and public `config`, stable IDs, original URLs, correct date units/timezones,
description text, all available locations and explicit salary/eligibility fields.
Retain `raw_data`. Reuse shared text/location/feed validation rather than changing
the normalized contract for one provider's JSON shape.

`fetch()` must have bounded complete pagination or reject unsupported pagination.
Missing detail must set `snapshot_complete=false` and remain observable. Declare
capabilities accurately. Use shared timeout/retry behavior and bounded concurrency;
detail-heavy adapters may need a small consecutive-failure circuit. `normalize()`
must never invent dates/salary/experience to satisfy a filter.

## 3. Wire all integration points

| File | Required consideration |
| --- | --- |
| `collectors/providers.py` | Add class factory and careers template |
| `collectors/ats_registry.py` | Correct access class, evidence, detection signatures, supported status |
| `collectors/discover.py` | Extract observed board/config and verify without activation |
| `shared/constants.py` | Extend `CollectorProvider` and `SourceType` literals |
| `services/api/app/schemas/sources.py` | Only necessary public config keys, strict values/host validation |
| `apps/web/types/jobs.ts`, `components/filters.tsx` | Keep visible provider types/options aligned; check provider badges/capability page |
| `.github/workflows/database.yml` | Add manual provider-recovery choice if the adapter is deployable |
| Tests and onboarding/support docs | Fixture contract, live evidence, known limitations and commands |

Search/storage/score rules should remain shared. Most providers do not require a
new SQLAlchemy model or migration. If adding a persistent field really is needed,
use an additive Alembic change and update response projections/contracts/tests.
Do not change the frozen matching engine just to make new-provider results look
better.

## 4. Test meaningful failure and repeat cases

Use injected `httpx` clients and representative public fixtures for complete/multiple
pages, changed totals, duplicate IDs, empty board, malformed row, missing description
or dates, multiple locations, explicit salary, unsafe link, timeout, transient
429/5xx, permanent 4xx and detail failure. Verify a partial snapshot cannot close
jobs. A complete empty board is a different case from a truncated board.

Run two syncs against an isolated database: identity must remain stable; unchanged
content should use the fingerprint path; changed content should update; removal
should follow configured complete-miss/deadline rules. Check cross-provider aliases,
source history and no full-body SELECTs on unchanged runs. Source failure must not
stop another provider. Optional live tests stay opt-in and separate from fixtures.

## 5. Verify employers and register deliberately

Verify complete nonempty real snapshots and all normalized rows. Keep provenance,
timestamps and failure reasons. The existing file verifier can export reviewed
records without DB writes:

```text
python -m collectors.verify_sources <candidate-records.json> --output artifacts/verified-sources.json --cache artifacts/live
```

For one already supported board, `python -m collectors.registry <provider> <board>
--company <actual-name>` verifies then registers in the selected database.
Workday additionally requires the discovered config JSON; use returned public
configuration, not invented identifiers. `collectors.seed_sources --file <file>`
imports trusted reviewed records but does not live-verify every board on each run.

Keep separate country/brand/acquired-company boards as distinct source identities.
Use consistent actual company names and existing normalization; do not claim
different URLs are different employers simply to increase coverage counts.

## 6. Production rollout and stopping point

Complete fixture/integration/CI checks, review secrets/host validation, update
configuration, then use the existing maintenance/ingestion workflows. Verify
actual production source history, postings, filtering, detail/application links,
repeat behavior and failure isolation. State measured scale and date. Leave blocked
boards rejected/deferred with reasons. Once the requested adapter works, stop;
accounts, email, queues and another matching rewrite are not prerequisites.
