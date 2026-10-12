# Phase 3 matching results

Compared 2026-10-08T15:24:31.652772+00:00 baseline with 2026-10-08T16:15:23.951314+00:00 after reprocessing. Both snapshots contain the same **11,327** active records from 57 employer boards. The local scheduler was paused for a consistent comparison; no new postings were downloaded.

## Measured changes

| Indicator | Before | After |
| --- | ---: | ---: |
| Active source records | 11,327 | 11,327 |
| Canonical records | 11,327 | 11,327 |
| Other role family | 7,794 | 7,044 |
| Technical title still Other | 148 | 8 |
| Ambiguous location (no known country) | 3,291 | 3,072 |
| No detected years | 4,296 | 3,853 |
| Preferred-only evidence | 72 | 131 |
| Score ≥80, all families/countries | 126 | 171 |
| Senior title with score ≥80 | 0 | 0 |
| Early title with 5+ years | 17 | 17 |
| Early title with score <50 | 22 | 45 |
| Stored conflict flags | 0 | 458 |
| Missing employer date | 0 | 0 |
| Remote classification | 2,873 | 2,873 |

Other coverage increased by 750 records; technical-title Other flags fell by 140. Ambiguous locations fell by 219 without guessing city-only locations. These are rule coverage/consistency measurements, not labeled accuracy. Senior high-score flags were already zero and remain zero. Early-title/high-year flags number 17 in both snapshots, with 16 overlapping IDs; they remain visible with hard score caps. Baseline flags sometimes represent preferred years, while after flags use required years.

Detected years increase, but comparison needs care: the baseline legacy field sometimes held preferred years; Phase 3 legacy fields expose required years, with preferences stored independently. Lower missing-year counts are extraction coverage, not proof every newly detected count is correct. More high-score jobs and more stored conflicts do not establish better precision. Early-title low scores increase because stricter requirements and management/ambiguity penalties can override title signals.

At the same seven-day cutoff, the old dashboard rules match 28 jobs and the new defaults match 27. This is eligibility/rule coverage, not a personal-fit judgment.

## Evidence, restrictions and safety

All 11,327 jobs carry matching version 3.0.0. 5,321 have supported skills (18,143 indexed job/skill relations). Explicit remote U.S. language occurs on 1,084 jobs; 6 have named allowed states, 8 have excluded states, and 168 retain time-zone wording. These counts include every stored active source record and do not imply a location restriction is mandatory.

No job requiring three or more years scores ≥80 (0); no conflict-flagged job scores ≥80 (0). Conflict reasons overlap:

| Reason | Records |
| --- | ---: |
| Senior title conflicts with a low required experience minimum | 195 |
| Substantial experience is requested without an explicit required year count | 214 |
| No-experience wording conflicts with a numeric requirement | 30 |
| Early-career title conflicts with a high required experience minimum | 23 |

The full dry run processed 11,327, changed 11,327, failed 0 (305.234 seconds). The write pass processed 11,327, changed 11,327, failed 0 (365.526 seconds). SQLite comparison of all source identities, URLs, raw payloads, titles/descriptions, employer/discovery timestamps, lifecycle fields, duplicate references and created timestamps reports **zero differences**. UUID additions/removals are zero. Raw JSON was preserved. Derived locations/skills are rebuilt in batches with per-row savepoints; provider normalization has an HTTP transport that rejects any network access.

## Concrete stored examples

| Title / employer | Role before → after | Level before → after | Score before → after | Required / preferred years |
| --- | --- | --- | --- | --- |
| Associate General Counsel, Commercial – Infrastructure / OpenAI | Cloud / Infrastructure → Other | associate → associate | 28 → 23 | 12 / None |
| Software Engineer II, Backend (Decisions Orchestration) / Affirm | Back-End → Back-End | mid → level_2 | 37 → 61 | None / None |
| Forward Deployed Engineer / Netic | Other → Software Engineering | unknown → unknown | 50 → 68 | 2 / None |
| Forward Deployed Engineer (FDE) - New Grad - 2026-2027 / Netic | Other → Software Engineering | entry → new_grad | 78 → 78 | None / None |
| Gusto Pro Core, Junior Account Manager / Gusto | Other → Other | manager → manager | 15 → 8 | 2 / None |
| Junior Account Manager / Smartsheet | Other → Other | manager → manager | 22 → 15 | 2 / None |

Audit examples and targeted tests address false-positive risks: nontechnical infrastructure wording in legal titles, generic testing/security titles outside software, hard requirements competing with friendly wording, and preferred years treated as mandatory. False-negative risks include forward-deployed and solutions titles left Other, level II treated uniformly as mid, and trainee architect/lead context. Final review also found that a business-domain exclusion could hide explicit technical occupations (Software Engineer, Hardware Health; Technical Support Engineer, Finance). The corrected occupation guard updated 51 saved records with zero failures in 7.721 seconds; subsequent role-only dry run verifies no remaining derived role changes. Examples are not a substitute for adjudicated dataset labels.

## Evaluation and implementation

The evaluation dataset contains **220 real postings**, sampled deterministically across all 20 families plus title/experience strata, including internships, associates, level I, no-experience, low-year, senior and misleading title cases. Application Support has only one available posting. Human labels, notes and reviewer remain blank. `python -m matching.evaluate` reports **0 human labels and null accuracy/precision/recall**. Human review must establish those metrics; this stratified sample is not prevalence-weighted.

Experience parsing now separates required and preferred bounds/evidence, written numbers, education equivalency, irrelevant numbers, explicit zero experience and ambiguity categories. Contextual seniority distinguishes new graduates and levels I/II/III. Central role aliases add mobile, solutions, DevOps/SRE, database and networking. Deterministic token rules extract 30 technologies. Fit scores use hard requirement caps; confidence is a separate uncalibrated evidence heuristic. [Matching methods and ranking](matching.md) document exact behavior and known interpretation limits.

Migration `4d3b3cd86b1c` adds evidence/bounds/category/confidence/conflict/version and remote-restriction fields, plus indexed `job_skills`. `9f83a21cb4d0` adds the active/freshness expression index and normalizes boolean storage from the saved conflict evidence. All four original CHECK constraints and foreign-key integrity are preserved. JSON uses PostgreSQL JSONB with SQLite JSON variants. The dashboard defaults to seven-day U.S. non-senior score ≥50 and freshness/fit/confidence order, with lexical relevance first during search. Quick filters, combined skills and advanced categories, concise card reasons/3–5 skills, and full detail evidence/conflicts/remote language are available.

## Validation

- Backend: **244 passed**, 9 optional live-network tests skipped. Known warnings: upstream FastAPI/Starlette deprecation and SQLite expression-index reflection; migration tests verify the index directly.
- Frontend: 8 component tests passed; ESLint, Prettier and TypeScript passed; production Next.js build passed.
- SQLite migration upgrade, downgrade and re-upgrade plus Alembic model comparison passed. PostgreSQL offline DDL compilation passed; no local PostgreSQL execution is claimed.
- Browser: **4/4 passed in Chrome**, covering strict 0–2-year, remote, combined skills, freshness, fit sorting, explanations, persistence, mobile overflow and source history. Edge completed an earlier 4/4 run but later intermittently closed its process; final validation used installed Chrome through `PLAYWRIGHT_CHANNEL=chrome`. Desktop, mobile and detail screenshots were visually inspected.
- Full second dry run: 11,327 processed, 0 changed, 0 failed (307.413 seconds). After the final role correction, the role-only dry run examined all 11,327 with 0 changes/failures. Post-migration 50-row full reprocessing dry run also changed 0; metadata maintenance does not modify job/source records.

## SQLite performance

Isolated replicas of the completed real-posting snapshot, synthetic identifiers, full descriptions and matching/skill/location distributions; raw provider payloads are omitted from replicas. Seven warm repetitions after one excluded warmup, page size 12, repository count/list and Pydantic response conversion. Freshness is seven days except the all-dates case. Timings do not include HTTP, browser rendering, concurrent production traffic or PostgreSQL. [Machine-readable measurements and query plans](phase3-performance.json).

| Query | 10k median / p95 ms | 25k median / p95 ms | 50k median / p95 ms |
| --- | ---: | ---: | ---: |
| default | 48.47 / 57.73 | 104.81 / 115.40 | 184.23 / 229.22 |
| search react | 57.24 / 64.17 | 99.47 / 124.82 | 190.52 / 218.13 |
| multiword search | 49.72 / 57.48 | 101.29 / 120.64 | 206.00 / 228.45 |
| remote python | 97.20 / 100.58 | 236.37 / 250.70 | 476.23 / 497.74 |
| qa skill | 4.37 / 8.48 | 4.29 / 8.81 | 5.08 / 10.70 |
| state tx | 40.06 / 46.03 | 102.09 / 106.36 | 216.23 / 229.64 |
| score sort | 47.29 / 51.58 | 104.75 / 105.48 | 223.96 / 262.77 |
| all dates search | 149.06 / 152.05 | 354.34 / 400.09 | 815.49 / 1414.78 |

The initial 50k default query median was 1,132.78 ms and multiword search was 1,616.79 ms. The active/freshness index plus correlated country eligibility reduced them to 184.23 and 206.00 ms, respectively, in the completed run. State and skill filters use existing covering indexes/primary keys; full query plans are preserved. Some QA/Playwright and TX cases match zero jobs in this snapshot; their timing does not demonstrate a populated page, while default/search/remote cases do.

Broad all-dates wildcard search remains the slowest case (50k median 815.49 ms, p95 1,414.78 ms), followed by remote/Python at 476.23 ms median. These are the next query-plan targets; no new search service was added. PostgreSQL full-text search and concurrency have not been measured.

Live SQLite planner estimates became stale after table rebuilding: the statistics query took 10,027 ms and chose a country-only location scan for each job. `ANALYZE` reduced it to 402 ms in the same local measurement. Refresh is now automatic after migrations, non-dry reprocessing and full syncs. Final local HTTP smoke measured health 240.33 ms, statistics 494.47 ms, and the seven-day dashboard list 107.20 ms. These are individual smoke timings, not percentiles.

The 30-minute local scheduler was resumed with `--wait-first` after snapshot verification. The preview remains at `http://localhost:3000/`; ongoing ingestion will naturally change later live counts.

## Known limits and Phase 4

No labeled accuracy claim is possible yet. English regex parsing can miss alternative requirements or section headings, and boilerplate/team-member descriptions can produce overly strict minima or management flags. Unknown city-only or global remote locations stay unresolved. Confidence is not calibrated, and skills are detected mentions rather than demonstrated proficiency or mandatory qualifications. Other still includes legitimate nontechnology postings; their presence is expected in employer feeds.

Before adding Phase 4 providers, review the 220 human-label rows and prioritize errors in the top-ranked technology cohort. Measure precision/recall and confidence behavior, refine alternatives and ambiguous locations, and measure PostgreSQL plans/concurrency. Then expand providers against this evaluation baseline. AI enrichment can remain optional and versioned after the deterministic baseline is judged.
