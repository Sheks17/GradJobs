# GradJobs Matching Audit

Frozen comparison of the same 11,327 active non-demo source records. The scheduler was stopped during capture and reprocessing. [Methods](matching.md) and [results](phase3-matching-results.md) explain comparability and limits.

Reproduce the current audit with `python -m matching.audit --json artifacts/audit.json --csv artifacts/review.csv`. Local baseline and after JSON/CSV exports are under `artifacts/phase3/`. A rerun after ingestion resumes will reflect the new live snapshot.

## Baseline before Phase 3

Generated: 2026-10-08T15:24:31.652772+00:00

Active non-demo source records; flags are deterministic review cues, not proven errors.

- Active jobs: **11,327**
- Canonical jobs: **11,327**
- High score jobs: **126**
- Missing experience: **4,296**
- Missing posting date: **0**
- Remote jobs: **2,873**
- Preferred only: **72**
- Stored conflicts: **0**
- Failed postings in history: **0**

## Score Bands

| Category | Jobs |
| --- | ---: |
| 0-9 | 7,914 |
| 10-19 | 390 |
| 20-29 | 46 |
| 30-39 | 475 |
| 40-49 | 5 |
| 50-59 | 1,643 |
| 60-69 | 17 |
| 70-79 | 711 |
| 80-89 | 56 |
| 90-100 | 70 |

## Role Families

| Category | Jobs |
| --- | ---: |
| Application Support | 1 |
| Back-End | 250 |
| Cloud / Infrastructure | 462 |
| Data | 542 |
| Front-End | 45 |
| Full-Stack | 155 |
| IT Support | 43 |
| Implementation | 113 |
| Other | 7,794 |
| Product Support | 27 |
| QA / Testing | 75 |
| Security | 350 |
| Software Engineering | 1,322 |
| Systems / Business Systems | 29 |
| Technical Support | 119 |

## Seniority

| Category | Jobs |
| --- | ---: |
| associate | 186 |
| director | 401 |
| entry | 72 |
| executive | 173 |
| internship | 174 |
| junior | 3 |
| lead | 849 |
| manager | 2,630 |
| mid | 118 |
| principal | 265 |
| senior | 1,840 |
| staff | 774 |
| unknown | 3,842 |

## Experience Minimum

| Category | Jobs |
| --- | ---: |
| 0 | 37 |
| 1 | 213 |
| 2 | 456 |
| 3 | 764 |
| 4 | 503 |
| 5+ | 5,058 |
| unspecified | 4,296 |

## Experience Categories

| Category | Jobs |
| --- | ---: |
| legacy | 11,327 |

## Flags

| Category | Jobs |
| --- | ---: |
| ambiguous_location | 3,291 |
| early_title_high_experience | 17 |
| low_score_early_title | 22 |
| technical_title_unknown_role | 148 |
| unknown_role | 7,794 |
| unquantified_experience | 229 |

## Reproduce

```sh
python -m matching.audit --json artifacts/phase3/audit.json --csv artifacts/phase3/review.csv --markdown docs/matching-audit.md
```

Review flags use stored title levels and effective required years (legacy preferred years before Phase 3). Ambiguous location means no normalized country in any location. Unknown role includes nontechnical occupations and is not automatically a classification failure. History failures are cumulative, not a matching precision metric.


## After Phase 3 reprocessing

Generated: 2026-10-08T16:15:23.951314+00:00

Active non-demo source records; flags are deterministic review cues, not proven errors.

- Active jobs: **11,327**
- Canonical jobs: **11,327**
- High score jobs: **171**
- Missing experience: **3,853**
- Missing posting date: **0**
- Remote jobs: **2,873**
- Preferred only: **131**
- Stored conflicts: **458**
- Failed postings in history: **0**

## Score Bands

| Category | Jobs |
| --- | ---: |
| 0-9 | 8,078 |
| 10-19 | 313 |
| 20-29 | 35 |
| 30-39 | 547 |
| 40-49 | 45 |
| 50-59 | 1,427 |
| 60-69 | 260 |
| 70-79 | 451 |
| 80-89 | 78 |
| 90-100 | 93 |

## Role Families

| Category | Jobs |
| --- | ---: |
| Application Support | 1 |
| Back-End | 252 |
| Cloud / Infrastructure | 339 |
| Cybersecurity | 170 |
| Data / Analytics | 525 |
| Database | 29 |
| DevOps / SRE | 110 |
| Front-End | 45 |
| Full-Stack | 153 |
| IT Support | 13 |
| Implementation | 131 |
| Mobile | 74 |
| Networking | 11 |
| Other | 7,044 |
| Product Support | 29 |
| QA / Testing | 32 |
| Software Engineering | 1,575 |
| Solutions Engineering | 576 |
| Systems / Business Systems | 90 |
| Technical Support | 128 |

## Seniority

| Category | Jobs |
| --- | ---: |
| associate | 163 |
| director | 401 |
| early_career | 9 |
| entry | 22 |
| executive | 172 |
| internship | 174 |
| junior | 3 |
| lead | 685 |
| level_1 | 14 |
| level_2 | 85 |
| manager | 2,630 |
| mid | 39 |
| new_grad | 57 |
| principal | 265 |
| senior | 2,004 |
| staff | 774 |
| unknown | 3,830 |

## Experience Minimum

| Category | Jobs |
| --- | ---: |
| 0 | 59 |
| 1 | 219 |
| 2 | 494 |
| 3 | 834 |
| 4 | 535 |
| 5+ | 5,333 |
| unspecified | 3,853 |

## Experience Categories

| Category | Jobs |
| --- | ---: |
| 0_1 | 29 |
| 0_2 | 669 |
| 1_2 | 13 |
| 1_3 | 26 |
| 2_3 | 20 |
| 3_plus | 834 |
| 4_plus | 535 |
| 5_plus | 5,333 |
| ambiguous | 215 |
| no_experience_required | 15 |
| unspecified | 3,638 |

## Flags

| Category | Jobs |
| --- | ---: |
| ambiguous_location | 3,072 |
| classification_conflict | 458 |
| early_title_high_experience | 17 |
| low_score_early_title | 45 |
| technical_title_unknown_role | 8 |
| unknown_role | 7,044 |
| unquantified_experience | 214 |

## Reproduce

```sh
python -m matching.audit --json artifacts/phase3/audit.json --csv artifacts/phase3/review.csv --markdown docs/matching-audit.md
```

Review flags use stored title levels and effective required years (legacy preferred years before Phase 3). Ambiguous location means no normalized country in any location. Unknown role includes nontechnical occupations and is not automatically a classification failure. History failures are cumulative, not a matching precision metric.
