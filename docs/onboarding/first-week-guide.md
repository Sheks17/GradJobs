# First week for a new developer

[Guide index](README.md)

Use an isolated local database and public fixtures. The exercises are for learning,
not a requirement to modify production or expand the completed MVP. Keep the
matching engine frozen unless a separate task authorizes a change.

## Day 1: boundaries and a working local app

Read [architecture](architecture.md), [repository map](repository-map.md) and
[local setup](local-setup.md). Start the API and frontend with demo data or one
verified local source. Enable demo visibility only for fictional data. Identify
where the root `.env` and web `.env.local` differ.

Trace one network request from Dashboard to `fetchApi`, the jobs route,
`JobFilters`, `list_jobs`, and `JobPage`. Explain why local `/jobs` and production
`/api/jobs` are the same logical endpoint, and why the browser never contacts
Neon directly. Deliverable: a short request trace with file/function names.

## Day 2: one provider and one row

Read [ingestion](ingestion.md), [database](database.md) and the first
[walkthrough](flows.md#follow-one-job-through-gradjobs). Start with the small
Greenhouse adapter/fixture before reading Workday. Compare raw fixture fields to
`NormalizedJob`, then to persisted `Job`, `JobLocation` and `JobSkill`.

Run its fixture tests and a bounded isolated sync. Confirm that a second identical
sync preserves identity and reports unchanged rows. Explain a source UUID,
board token, provider posting ID and internal job UUID without treating them as
interchangeable. Deliverable: an annotated single-job map and repeat-sync evidence.

## Day 3: requirements and search semantics

Read [matching](matching.md), [search](search.md) and the second
[walkthrough](flows.md#follow-one-user-search). Use a Python REPL with synthetic
title/description strings and call `score_job`; this computes values without DB
writes. Compare required vs preferred years, unknown experience, a junior title
with high requirements, and management wording. Do not invent labels for holdout
postings or overwrite reviewed reports.

Reproduce React + Remote + Last 7 Days via API parameters. Explain why typing
React differs from selecting the React skill, and why a high-scoring older role
can rank below a fresh role. Deliverable: explain score versus confidence and
the scope of result count versus dashboard statistics.

## Day 4: frontend state and failure handling

Read [frontend](frontend.md) and [debugging](debugging.md). Save/reload/delete a
local search, open a detail to record viewed status, and track an application.
Inspect the two browser storage keys using development tools. Use a disposable
browser profile for clearing-storage exercises.

Stop the local API to observe errors, restore it, and retry. Check why statistics
may show dashes independently of job results. Run the Vitest suite; inspect the
Playwright setup before starting browser tests. Deliverable: explain what persists
across reloads, what is lost on another origin, and how obsolete requests abort.

## Day 5: production operations and a small reviewable change

Read [deployment](deployment.md), [testing](testing.md), [security](security.md)
and [adding a provider](adding-a-provider.md). Inspect the three Actions workflows
without dispatching production work as a learning exercise. Find the PostgreSQL
guard, repository secret references, shared concurrency group, migration step,
cache restore/save and artifact uploads. Inspect recorded restoration evidence.

Practice choosing the right diagnosis for a quota outage, malformed source row,
empty filtered result, expired posting and failed browser save. Then make a small
documentation or meaningful local regression improvement, run the relevant checks
and explain the scope. Deliverable: a reviewable change plus a concise account of
what was verified and what remains unknown.

## Questions you should be ready to answer

1. Where exactly does `/jobs` bind filters, construct SQL and render cards?
2. Why does Workday need tenant/site configuration and detail caching?
3. What prevents a failed provider fetch from closing all its existing jobs?
4. How do deduplication, stable source identity and unchanged fingerprints differ?
5. Why does “unknown required experience” not mean “no experience required”?
6. Why can provider health look healthy before the current full run completes?
7. How are production secrets kept out of frontend bundles and public source JSON?
8. Which tests exercise PostgreSQL and which use SQLite or mocked HTTP?
9. Why does a small database still risk high network transfer?
10. What would you inspect before adding infrastructure or changing matching?

For an interview, describe the problem, the implemented pipeline and the evidence
with scope: explainable early-career discovery from multiple employer sources,
isolated scheduled ingestion, one normalized model and practical production cost
controls. Cite dated scale and reviewed-sample metrics rather than claiming
universal accuracy or real-time coverage. Be candid about browser-local tracking,
best-effort scheduling and pending independent human review.
