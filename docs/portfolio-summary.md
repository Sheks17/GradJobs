# GradJobs portfolio summary

GradJobs is a multi-source job discovery platform for early-career technology
candidates. It collects public employer ATS postings and USAJOBS records, converts
inconsistent payloads into a shared validated model, deduplicates listings, tracks
freshness and closures, and ranks opportunities with explainable deterministic
rules. The Next.js interface supports search, filters, job explanations,
browser-local saved searches and application tracking.

The production system separates request-serving Next.js/FastAPI services on Vercel
from scheduled GitHub Actions ingestion into managed PostgreSQL. Provider retries,
source leases, concurrency limits, transactional writes, failure cooldowns and
persisted run summaries make failures observable and isolated.

Measured scale, provider counts, performance, tests and verification dates are
maintained in [the MVP report](mvp-completion.md); current counts come from the
public API rather than hardcoded UI marketing numbers. The reviewed 220-posting
classification sample achieved 100% precision, 98.7% recall and 99.4% F1. These
results describe that sample, not universal accuracy. A separate holdout is left
unlabeled for independent human validation.

- [Live application](https://gradjobs-drab.vercel.app)
- [GitHub repository](https://github.com/Sheks17/GradJobs)
- [Engineering decisions and tradeoffs](design-decisions.md)

For interviews, explain the distinction between verified provider access, complete
source snapshots, ranking heuristics and reviewed accuracy. A score is a relevance
guide, not a personal resume assessment or hiring probability. Describe your own
implementation, review and testing contributions accurately, including any AI
tool assistance.
