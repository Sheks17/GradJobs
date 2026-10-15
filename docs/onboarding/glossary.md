# Glossary

[Guide index](README.md)

| Term | Meaning in this codebase |
| --- | --- |
| ATS | Applicant tracking system that hosts an employer's postings/applications |
| Provider | A platform adapter such as Greenhouse or Workday; USAJOBS is the federal provider |
| Source | One configured board or bounded federal query group, stored as `JobSource` |
| Board identifier | Public provider account/board token; not a GradJobs UUID or arbitrary URL |
| Tenant/site/shard | Workday account, careers board and observed hostname variation used to build CXS requests |
| CXS | Workday public careers endpoint family used by the implemented adapter |
| Snapshot | Set of rows a collector reports for one source fetch |
| Complete snapshot | Entire configured source scope fetched successfully, with no known missing page/details; required for closure reconciliation |
| Normalization | Mapping inconsistent provider data into validated shared fields |
| `NormalizedJob` | Pydantic provider-to-ingestion payload; not an ORM row or public API response |
| ORM | SQLAlchemy's Python model abstraction over SQL rows/queries |
| Pydantic | Validation and serialization library for settings/payloads/API models |
| Internal job ID | GradJobs UUID used by `/jobs/{id}` and browser tracking |
| `source_job_id` | Stable posting identifier inside one source; paired with source UUID for uniqueness |
| External/requisition ID | Optional employer-facing reference; may differ from stable provider/internal IDs |
| Upsert | Existing source/job identity gets updated; absent identity gets inserted |
| Canonical job / alias | Visible representative versus retained row pointing to it through `duplicate_of` |
| Description fingerprint | Hash of normalized description used for conservative duplicate comparison |
| Ingestion fingerprint | Hash of normalized source content used to avoid unchanged-row upserts/body reads |
| Matching version | Version of derived rule outputs; currently frozen at `3.0.0` |
| Required vs preferred | Mandatory detected experience versus desirability evidence stored independently |
| Score | 0–100 early-career suitability heuristic, not personalized resume similarity |
| Classification confidence | Evidence-strength heuristic, not a calibrated probability |
| Cutoff | Default minimum score 50 for results/evaluation; does not delete lower-scoring rows |
| Freshness | Posting date when known, otherwise first discovery; separate from observation/update |
| `first_seen_at` / `last_seen_at` | Initial GradJobs discovery versus most recent successful observation |
| `closing_at` / `closed_at` | Employer deadline versus timestamp GradJobs marked inactive |
| Lifecycle reconciliation | Counting absence only after complete snapshots and closing after configured thresholds |
| SourceSync / IngestionRun | One source attempt versus one aggregate full/provider-filtered invocation |
| Lease | Token/expiry ownership preventing concurrent work on one source |
| Advisory lock | PostgreSQL transaction lock coordinating write sections without external infrastructure |
| Savepoint | Nested transaction boundary allowing one upsert attempt to roll back locally |
| Circuit / cooldown | Stop repeated detail requests within a run versus defer repeatedly failing sources across attempts |
| Projection / `load_only` | Selecting only needed database columns rather than loading large full rows |
| JSONB | PostgreSQL's JSON storage type used for raw data, evidence, configuration and summaries |
| Alembic revision | Ordered schema migration identifier; separate from the Git commit or matching version |
| ASGI | Python interface used to serve FastAPI through Uvicorn/Vercel |
| App Router | Next.js file-based routing under `apps/web/app` |
| Client component | React component executing browser interactions/hooks, declared with `use client` |
| Hydration | React attaching browser behavior to the initial rendered page |
| localStorage | Browser-origin storage holding tracking/searches; not PostgreSQL or cross-device persistence |
| AbortController | Cancels obsolete fetches so old results do not replace current filters |
| CORS | Browser cross-origin policy; not user authentication |
| SSRF | Untrusted URL input causing a server to access unintended/private destinations |
| Egress | Data transferred outward from Neon; separate from stored size or provider response traffic |
| Holdout | Independent unlabeled-then-human-reviewed postings reserved for later evaluation |
| Precision / recall | Fraction of predicted positives correct / fraction of actual positives found in labeled evaluation |
| F1 | Harmonic mean of precision and recall on the evaluated labels |
| MVP | Implemented usable baseline; optional future features are not new completion blockers |
