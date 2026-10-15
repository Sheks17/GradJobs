# Search, filters and ranking

[Guide index](README.md) · [Query implementation](../../services/api/app/repositories/jobs.py)

## Visibility before preference filters

`visible_conditions()` requires active jobs, no `duplicate_of` pointer, and no
elapsed explicit closing deadline. Country defaults to U.S. and can match the
primary job country or any relational `JobLocation`. `country=all` removes that
condition. There is no public inactive-jobs switch for the list; detail retrieval
can still show a retained closed posting for application tracking.

`list_jobs()` excludes role family `Other` unless an explicit role family is
provided. It then applies score, seniority, demo, text, skills, experience,
geography, company, salary and date predicates. Filters combine with AND unless
the implementation explicitly expresses alternatives inside a predicate.

## Default dashboard versus bare API

| Behavior | Dashboard | Bare `/jobs` API |
| --- | --- | --- |
| Country | US via API default | US |
| Active/canonical/unexpired | Required | Required |
| Score ≥50, non-senior, no demo | Defaults | Defaults |
| Experience | Required minimum ≤3 or unknown | Same default |
| Freshness | Last seven days sent as `fresh_after` | No date filter unless supplied |
| Page size | 12 | 20 |
| Ordering | `best_match` | `best_match` |

The UI allows broadening date/score/experience and including senior/demo roles.
It does not expose every API option: for example the API accepts `country=all`,
but the current dashboard is U.S.-focused. Unknown experience means no required
minimum was extracted, not “zero years required.”

## Text and skill semantics

Each of the first 12 whitespace-separated search tokens must match at least one
of title, company, role, canonical skill, or description. Alternatives within one
token are OR; successive tokens are AND. `%`, `_` and backslashes are escaped
for literal substring matching, and SQLAlchemy binds parameters.

Relevance weights per token use the first matching CASE branch: title 100,
company 70, role 30, canonical skill 20, otherwise description 5. Those branches
are not added together for the same token. Description conditions execute in
PostgreSQL without transferring the description into the list response.

The separate `skill=React` filter uses canonical `JobSkill` rows. Searching text
`q=React` can also match a description or title; it is not identical to selecting
the skill control. There is no stemming, semantic vector search, Elasticsearch
or PostgreSQL `tsvector` full-text pipeline in the current code. The implemented
text search is SQL substring matching plus the vocabulary lookup.

## Experience, salary and remote details

Versioned jobs filter by `required_min_years`; old unversioned rows use the legacy
experience minimum until reprocessed. Preferred years do not become a mandatory
minimum. Explicit experience categories are an additional independent condition.

Minimum salary compares disclosed `salary_min` only when currency is USD and
period is yearly. It does not annualize hourly pay or compare unknown currencies.
Unknown salary therefore cannot satisfy a minimum salary filter.

State filtering normalizes names/codes and considers primary plus additional
locations. Remote type is a separate field. Restriction evidence (allowed and
excluded states, U.S.-only language, timezone) is displayed metadata; the current
query does not resolve a user's personal eligibility from those fields. Selecting
“Remote” does not prove that a user in any state can apply.

## Dates and order

Freshness is `coalesce(posted_at, first_seen_at)`. `fresh_after` uses that value;
`posted_after` requires a source posting date. An old known posting does not become
fresh merely because it was rediscovered or updated today. `last_seen_at` proves
observation, not publication. `NEW` uses recent discovery separately.

For `best_match`/`relevance`, a text query puts accumulated relevance first. Next
come freshness bands (within one day, three days, seven days, older), score
descending, confidence descending and freshness descending. Without a text query,
the same quality order begins with the freshness band. Thus a fresh possible fit
can appear above an older excellent fit. Other sort modes use their named date,
company or annual-USD salary behavior. `Job.id` is appended for deterministic
tie-breaking.

The repository first counts matching rows, then applies offset/limit. Pagination
is not a cursor or immutable snapshot; concurrent ingestion may shift results
between page requests. The frontend computes a rolling date cutoff and fetches
fresh JSON. See [flows](flows.md) for the complete React-to-SQL path.

## Interpreting counts

Result total is the number matching these filters. Dashboard statistic cards are
all-visible U.S. aggregates and include roles beyond the current search. Provider
counts are global canonical active non-demo counts, and source `active_jobs`
counts can include duplicate aliases. These scopes are intentionally different.
`last_successful_sync` in stats is the maximum per-source success, not proof that
the last full ingestion run succeeded. Use `/ingestion` for that question.
