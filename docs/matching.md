# Phase 3 deterministic matching

Matching version `3.0.0` uses English title and description rules. There are no LLM calls, embeddings, resumes, or personal profiles. A fit score measures early-career signals, not hiring likelihood. The separate classification confidence is an uncalibrated evidence heuristic, not a probability.

## Experience and title context

The parser stores independent required/preferred bounds, requirement type, category, matched text, confidence, and every evidence span. It recognizes numeric and written zero-to-twenty years, ranges, plus signs, minimum/at-least/up-to/less-than wording, and explicit no-experience statements. Required and preferred section headings apply until another recognized heading. The strictest required minimum wins; preferred experience cannot replace it. Education/experience equivalency and certification validity are excluded from hard work-year requirements. Education alternatives without another numeric requirement remain ambiguous.

Unknown required years remain null. Preferred-only records have an unspecified required category. `0_2` also groups single/open minimums below three when they do not match a named range; it does not promise an upper bound. Less than three is stored as whole years 0â€“2; the original evidence remains available. The maximum-experience filter compares the acceptable required minimum, not the upper range. Disabling unspecified experience requires an explicit numeric/zero required minimum.

Title context allows Junior Solutions Architect, Cloud Architect Intern, Associate Technical Lead Program, Graduate Leadership Program, Junior Project Lead, and Entry-Level Security Architect. Explicit senior/staff/principal/manager wording still wins. Scoped Engineer/Analyst/Developer/Administrator/Specialist I maps to level 1, II to level 2, III to mid. Numeric levels alone do not establish fit: descriptions can cap the score and trigger conflict flags. Bare technical titles remain unknown.

`matching/aliases.py` is the central ordered role mapping. Support, implementation, QA, mobile, database, DevOps/SRE, networking, cybersecurity, systems and data patterns precede generic software rules. Nontechnical legal, recruiting, finance, marketing and physical engineering titles remain Other; explicit technical occupations take precedence over business-domain exclusions. There are 20 selectable families. Lower Other counts are coverage evidence, not proof of accurate classification.

## Fit score and confidence

Start at 50. Early titles add 28 (internship 20); level II adds 4; mid subtracts 12; senior titles subtract 60. Explicit no experience adds 35. Required minimum 0â€“1 adds 25; 2 adds 18; a 1â€“3 or 2â€“3 range adds 18. Minimum 3 subtracts 20, 4 subtracts 35, 5+ subtracts 55. Preferred-only minimum â‰¤2 adds 8, 3 subtracts 4, 4+ subtracts 8. Accepted internship experience adds 8; graduate/training signals add 10; a bachelor's degree without high required years adds 7. Unquantified substantial experience subtracts 18, explicit people management 25.

Hard caps prevent positive title signals from overriding required years: 3 caps at 49, 4 at 40, 5+ at 25. Senior titles cap at 29; people management at 40; extensive experience at 49. Structured positive/negative/neutral reasons explain each change, including any cap adjustment. The fit labels remain Excellent (85+), Strong (70+), Possible (50+), Stretch (30+), and Experienced (below 30).

Confidence starts at 40, increases for recognized title/role and explicit numeric requirements, and decreases for ambiguity, short descriptions and conflicts. It is clamped to 15â€“98. Conflicts include early title with high required years, senior title with low required years, early title with management, unquantified substantial experience, and zero-experience wording contradicted by required years. Confidence measures rule evidence clarity, not whether the applicant qualifies.

## Locations and skills

Location normalization understands full U.S. state names, remote/hybrid prefixes, slash/or-separated locations, and structured provider locations. Unknown cities and global remote eligibility remain unknown. State-only inputs do not invent a city. Explicit remote U.S. language, allowed/excluded states, and time zone wording are retained separately with source evidence. A time zone preference is preserved as wording; it is not silently promoted to a hard restriction.

`matching/skills.py` extracts the 30 supported terms deterministically with token boundaries and conservative disambiguation. JavaScript does not imply Java, GitHub does not imply Git, and NoSQL does not imply SQL. Skill presence does not indicate required proficiency. JSON stores the display list; `job_skills` provides a unique job/skill relation with a covering `(skill, job_id)` index. The frontend obtains role/skill options from `/metadata`.

## Search and default ranking

The dashboard defaults to active, canonical, non-demo U.S. technology jobs from the last seven days, excluding senior titles, score â‰¥50 and required minimum â‰¤3, including unspecified required experience. Other roles can be explicitly selected. Freshness uses the employer date, falling back to first discovery only when that date is missing.

Search splits up to twelve tokens and requires each in title, company, family, normalized skills, or description. Per-token title/company matches score 100/70, family 30, skill 20, description 5. With a query, lexical relevance comes first. Otherwise default order is freshness bands (last day, three days, seven days, older), fit descending, confidence descending, exact freshness descending, then stable UUID. Search relevance uses the same order. Explicit newest/score/company/salary sorts remain available. Scores do not obscure hard eligibility requirements.

SQLAlchemy LIKE escaping and relational skill/location predicates work on SQLite and PostgreSQL. No extra search service is needed. PostgreSQL full-text search remains an optional future query adapter: add a weighted generated document and GIN index only after measuring actual PostgreSQL plans and validating language/token behavior against human judgments. The current wildcard description scan is the identified scale risk. PostgreSQL execution was unavailable locally; portable DDL compilation is checked and CI is configured for PostgreSQL.

## Audit, reprocessing and evaluation

```sh
python -m matching.audit --json artifacts/phase3/audit.json --csv artifacts/phase3/review.csv --markdown docs/matching-audit.md
python -m matching.reprocess --dry-run --output artifacts/phase3/dry-run.json
python -m matching.reprocess --source greenhouse
python -m matching.reprocess --output artifacts/phase3/reprocess.json
python -m matching.sample_evaluation --output data/evaluation/new-sample.json --size 220
python -m matching.evaluate --input data/evaluation/jobs.json
python -m matching.benchmark --output-dir artifacts/phase3/new-benchmark
```

Reprocessing normalizes retained provider payloads with a transport that forbids HTTP, updates only derived fields and relational skills/locations, uses bounded atomic batches and isolates individual failures. It preserves UUID, source identity, URLs, payload, first/last discovery, employer date, lifecycle and duplicate relationship. Dry runs roll back without writes; source and limit filters are supported. Keep a database backup and freeze the scheduler when comparing snapshots.

`--changed-roles-only` skips already-versioned jobs whose derived role is unchanged, allowing a narrow role-rule correction without repeating every description parse. SQLite planner statistics refresh after migrations, non-dry reprocessing, and full scheduled syncs. Stale estimates can otherwise cause a country-only location scan for every job. The active/freshness expression index and correlated country/skill/state eligibility predicates avoid fetching large match-ID sets before filtering by freshness. SQLite cannot reflect expression indexes through the current SQLAlchemy/Alembic combination; migration tests check their existence directly.

Audit flags are review cues, not proven errors. Ingestion failure counts are cumulative source history, not parser accuracy. The evaluation file contains real descriptions, identifiers, original URLs, unverified stored predictions, nullable human labels, notes and reviewer. Sampling deliberately covers role and experience/title strata; it is not prevalence-weighted. Sampling refuses to overwrite an existing label file. Evaluation only uses valid human labels and returns null metrics when none exist. Human review should establish precision, recall and error categories before optional AI enrichment or additional providers.

The [validation workflow](phase3-validation.md) uses `data/evaluation/review.csv`; it includes current prediction snapshots, full retained descriptions, and blank human-review fields. `python -m matching.review` exports a new file and refuses overwrites. `python -m matching.evaluate` automatically joins the CSV beside its JSON input, validates review provenance, and recomputes current predictions. It provides per-class and binary metrics, thresholds 50/60/65/70/75/80, role/experience/confidence breakdowns, reviewer error categories, and diagnostic rows. Use `--output` for JSON and `--markdown` for the validation report. No labels, production thresholds, or confidence rules are changed automatically.

Scale benchmarks clone real descriptions and matching distributions into isolated SQLite files with synthetic IDs. They measure the full repository list/count plus serialization, seven warm repetitions after one excluded warmup, twelve items per page; this is not a production concurrency/network or PostgreSQL benchmark. The live database is never populated with benchmark replicas.
