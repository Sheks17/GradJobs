# GradJobs developer onboarding

This is the repository-first engineering guide for a new developer. It describes
implementation inspected at commit `62ecfa6`, not a proposed future architecture.
Read the source links when changing behavior; names and defaults can evolve.
Operational counts are dated observations, never promises about current coverage.

## What GradJobs does

GradJobs helps U.S. early-career technology candidates find employer postings,
understand the requirements behind a recommendation, and track applications.
It fetches registered public ATS boards and scoped USAJOBS searches, validates
provider data, retains provenance, groups conservative duplicates, and stores
explainable deterministic classifications. Users search that stored dataset and
apply on the original employer site. The browser never waits for an ATS crawl.

Eight ATS adapters and one federal adapter ingest jobs: Greenhouse, Lever, Ashby,
SmartRecruiters, Workday, Workable, Recruitee, BreezyHR, and USAJOBS. The larger
ATS capability registry includes detection-only providers. Recognizing a platform
does not mean its jobs can be retrieved. Scheduled refreshes use the configured
source registry; broader employer discovery is an operator-driven CLI workflow.

There are no user accounts, resume uploads, personalized AI recommendations,
cross-device tracking, or email alerts. Saved searches and application statuses
are browser-local. A score expresses fit evidence, not an employer's hiring
decision or a probability of success.

## Read this guide

| Guide | What you should understand afterward |
| --- | --- |
| [Architecture](architecture.md) | Process boundaries and engineering decisions |
| [Repository map](repository-map.md) | Where to start for a change |
| [Frontend](frontend.md) | Pages, components, React state and local storage |
| [Backend](backend.md) | Routes, sessions, schemas and repositories |
| [Database](database.md) | Six models, relationships, indexes and migrations |
| [Ingestion](ingestion.md) | Provider contracts, normalization, deduplication and lifecycle |
| [Matching](matching.md) | Extraction, classification, scoring and validation |
| [Search](search.md) | Filter semantics, ranking and pagination |
| [API reference](api.md) | Every declared application endpoint |
| [End-to-end flows](flows.md) | Follow one Workday job and one React search |
| [Local setup](local-setup.md) | Start with an isolated local database |
| [Deployment](deployment.md) | Vercel Services, Neon and GitHub Actions |
| [Testing](testing.md) | Which checks prove which behavior |
| [Security and limitations](security.md) | Trust boundaries and implemented safeguards |
| [Debugging](debugging.md) | Find the failing layer before changing code |
| [Adding a provider](adding-a-provider.md) | Complete integration checklist |
| [Glossary](glossary.md) | Domain and framework terms |
| [First week](first-week-guide.md) | Practical learning sequence and exercises |
| [Source index](source-index.md) | Runtime modules, symbols and line references |

Start with architecture, flows and local setup. Then follow the first-week guide.
This collection is also a handoff package for creating a teaching handbook: use
the actual file/function references and preserve the distinctions called out here.

## Evidence and maintenance

The [production restoration report](../production-restoration.md) records a
99/99-source cloud recovery, 17,355 active canonical jobs across all countries,
9,662 U.S. jobs, and 102 verified employers including disabled candidates. These
were measured around 15 October 2026 00:19 UTC, not remeasured for this guide.
The release had 346 backend, 13 frontend and nine browser tests passing. This
documentation task does not claim a new execution of those application suites.

The reviewed 220-posting sample reported 100% precision, 98.7% recall, 99.4% F1
and 99.1% four-class accuracy at cutoff 50. Those figures apply to that reviewed
sample; independent holdout labels remain pending. See [matching](matching.md).

When changing a feature, update its guide, its contract tests and the source
index if symbols move. Never copy `.env`, credentials, reviewer data, database
dumps or generated deployment state into documentation. Links in these files are
repository-relative so the same guide works on GitHub and a fresh checkout.
