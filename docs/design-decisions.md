# GradJobs design decisions

## Next.js and FastAPI
**Problem:** An interactive search interface and Python ingestion/classification have different concerns.
**Approach:** Next.js renders the React interface; FastAPI validates queries and exposes the shared database.
**Alternatives:** A Python-only rendered UI or a JavaScript-only application.
**Tradeoff:** Two runtimes and deployment configuration, with clear boundaries and reusable Python tooling.

## PostgreSQL, with SQLite for development
**Problem:** Hosted data must survive deployments and support concurrent readers, structured metadata and filtering.
**Approach:** PostgreSQL in production, SQLAlchemy/Alembic for access and versioned schema changes; SQLite is a local fallback.
**Alternatives:** Files, hosted SQLite, a document database or an external search service.
**Tradeoff:** PostgreSQL requires managed credentials and migrations. SQLite cannot prove PostgreSQL behavior, so CI runs migrations and tests against PostgreSQL.

## Scheduled ingestion and GitHub Actions
**Problem:** External providers are slow, can fail, and should not delay visitor requests.
**Approach:** GitHub Actions collects jobs independently of the Vercel request-serving API, with repository secrets, artifacts, manual dispatch and concurrency controls.
**Alternatives:** Collection during API requests, a laptop scheduler, or persistent queue workers.
**Tradeoff:** Cron is approximate and runs can take longer than their trigger interval. It is adequate for the MVP without another service; freshness is observed, not advertised as real-time.

## Normalization before matching and storage
**Problem:** Providers disagree on identifiers, dates, locations and descriptions.
**Approach:** Adapters produce one validated NormalizedJob contract; shared ingestion normalizes text and URLs, classifies, deduplicates and writes related filter tables. Raw payloads remain available for diagnosis.
**Alternatives:** Provider-specific tables or transformation in each frontend component.
**Tradeoff:** Some provider detail remains metadata rather than universal fields; absent information stays unknown.

## Deterministic classification and score-based ranking
**Problem:** Junior titles can conceal substantial experience requirements; users need understandable relevance.
**Approach:** Versioned rules extract requirements, seniority, role families and skills; scores and evidence support ranking and filtering.
**Alternatives:** Binary title filtering, LLM classification, or trained recommendation models.
**Tradeoff:** Rules are reproducible and inexpensive but can miss unusual language. Scores and confidence are heuristics, not hiring probabilities or guarantees.

## Operational cutoff 50
**Problem:** A default must balance accessible opportunities and misleading experienced roles.
**Approach:** Keep cutoff 50 and matching version 3.0.0 frozen after the reviewed 220-posting evaluation.
**Alternatives:** Higher precision-oriented thresholds or lower recall-oriented thresholds.
**Tradeoff:** Reviewed-sample precision 100% and recall 98.7% do not establish universal accuracy. A fresh holdout is human-labeled before any tuning.

## Original ATS endpoints and USAJOBS
**Problem:** Aggregated listings can be stale, duplicate, or disconnected from actual applications.
**Approach:** Collect public employer ATS data and the official federal API; application links lead to original postings.
**Alternatives:** LinkedIn/Indeed scraping or a commercial aggregator.
**Tradeoff:** Coverage is incomplete and provider APIs can change. There is no challenge bypass or fabricated employer configuration.

## Provider isolation, complete snapshots and cooldowns
**Problem:** A single failed detail or outage must not stop ingestion or incorrectly close postings.
**Approach:** Bounded HTTP retries, source leases, provider concurrency, per-posting savepoints, complete-snapshot reconciliation, failure counters and timed cooldowns. Sources remain registered and flagged for review.
**Alternatives:** Global fail-fast collection, immediate deletion, or external circuit-breaker infrastructure.
**Tradeoff:** Partial runs preserve safety at the expense of delayed closures. Permanent errors remain observable rather than being retried endlessly within one run.

## Browser-local application tracking and saved searches
**Problem:** Users need organization without making accounts or supplying personal data.
**Approach:** Store application status and named filter combinations in localStorage; load searches against current listings.
**Alternatives:** Server accounts and synchronized personal records.
**Tradeoff:** Data is browser/device-specific and can be lost when storage is cleared. Email delivery and account-based notification evaluation remain future work.

## Workday requires separate treatment
**Problem:** Workday uses tenant, hostname shard, locale and site-specific CXS endpoints; summaries omit descriptions and exact dates.
**Approach:** Derive configuration from observed careers URLs, validate approved Workday hostnames, paginate against the initial count, fetch details with bounded concurrency and normalize stable posting IDs.
**Alternatives:** Hardcoding one company, guessing tenant/site names, or accepting summaries as full jobs.
**Tradeoff:** Initial imports require many detail requests; blocked tenants and endpoint limits are reported, not bypassed. Relative "Posted 30+ days" text never becomes an invented exact timestamp.

## Production operations are read-only
**Problem:** A public demonstration must not let anonymous visitors alter sources or launch syncs.
**Approach:** Disable source mutation and sync endpoints in production. The ingestion page exposes aggregate operational history only; GitHub Actions is the authenticated operations path.
**Alternatives:** An admin token or full OAuth.
**Tradeoff:** No in-browser production administration; avoids additional credential handling and unnecessary authentication infrastructure for the MVP.
