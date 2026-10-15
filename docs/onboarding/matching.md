# Matching and classification

[Guide index](README.md) · [Scoring source](../../matching/scoring.py) ·
[Reviewed validation](../phase3-validation.md)

## Inputs and outputs

`score_job(title, description)` is a deterministic pure calculation. It produces
a frozen `MatchResult`: role, seniority, required/preferred bounds, experience
evidence/category/confidence, early-career score, label, scoring reasons/points,
classification confidence/conflicts, skills and matching version `3.0.0`.
Ingestion persists these fields; search normally reads them rather than rescoring
every request. No resume, account profile, LLM call or external inference service
is involved. Do not casually tune the frozen engine while editing ingestion/docs.

## Modules and their order

1. [role_classifier.py](../../matching/role_classifier.py) classifies seniority and
   role from normalized title. Senior responsibility patterns take precedence;
   junior/trainee occupational architect cases and role-adjacent I/II/III levels
   have explicit handling. Role aliases are ordered, so the first match matters.
2. [experience.py](../../matching/experience.py) scans description lines with
   required/preferred heading context and inline qualifiers. It handles numeric
   and written years, ranges, minimum/up-to/less-than wording and explicit
   no-experience statements. History/certification validity and education
   equivalency contexts are excluded or marked ambiguous.
3. [scoring.py](../../matching/scoring.py) combines title, experience, early-career
   wording, management/extensive-experience evidence, confidence and hard caps.
4. [skills.py](../../matching/skills.py) extracts vocabulary matches from title plus
   description. Token boundaries avoid Java/JavaScript confusion and preserve C#,
   C++ and other punctuation. Some ambiguous words deliberately require case.

Required and preferred evidence remain independent. Where multiple required
minimums are found, the extractor chooses the highest minimum, not the first
small number. No numeric minimum detected is `unspecified` or `ambiguous`, not
automatically zero. The output retains snippets and offsets for inspection.

## Score mechanics

The score starts at 50. Early-career titles add evidence; senior titles subtract
60. A required minimum of zero/one generally adds 25, two adds 18, three subtracts
20, four subtracts 35, and five or more subtracts 55. Explicit no-experience
wording adds 35. Preferred-only experience has smaller effects. Early-career
signals and a bachelor's mention without a high mandatory minimum can add points.
Management and extensive-experience wording subtract points.

Hard caps prevent positive phrases from overruling high mandatory requirements:
minimum three caps at 49, four at 40, five-plus at 25; senior titles cap at 29;
management at 40 and substantial experience at 49. The final score is bounded
0–100. Read the implementation for contextual range exceptions and the full
evidence list rather than recreating the algorithm from this prose.

| Score | Fit label |
| --- | --- |
| 85–100 | Excellent Early-Career Fit |
| 70–84 | Strong Early-Career Fit |
| 50–69 | Possible Fit |
| 30–49 | Stretch |
| 0–29 | Experienced Role |

Confidence is a separate evidence-strength heuristic bounded 15–98. It increases
with clearer title/requirement signals and falls for ambiguous wording, conflicts
or very short descriptions. It is not a calibrated probability. A neutral title
with unknown requirements can score 50 while confidence remains modest.

Example: “Junior Software Engineer” with an explicit five-year required minimum
can generate conflicting early-title/high-minimum evidence and remain below the
operational cutoff. This is why title matching alone is not the classifier.

## Cutoff and evidence

The operational cutoff is 50, implemented as a query/UI default, not a database
rule deleting jobs below it. Users can broaden filters. Classification confidence
breaks ranking ties and is displayed; it is not a mandatory confidence filter.
`score_evidence` explains positive/negative/neutral contributions, while
`experience_evidence` preserves the input requirements behind bounds.

The reviewed 220-job sample reported precision 100%, recall 98.7%, F1 99.4%,
four-class accuracy 99.1%, zero false positives and one false negative. These
metrics are sample-specific and the sample is not prevalence-weighted. They do
not establish universal accuracy, particularly for newer provider populations.
Federal specialized experience can describe grade/eligibility pathways rather
than ordinary graduate work experience; unusual supervisory wording remains a
documented limitation. Users must read the original employer requirements.

## Evaluation and safe changes

`sample_evaluation.py` builds review datasets; `review.py` exports human-review
CSV and validates imported labels/identity/content; `evaluate.py` computes metrics
only from human-labeled rows. `validation_report.py` renders diagnostics.
`sample_holdout.py` excludes previous IDs, source URLs and title/description
fingerprints, creating new unlabeled review files without overwriting existing
review. The 150-job holdout and newer-provider review extension remain for human
validation; never infer labels from model predictions to claim accuracy.

`audit.py` surfaces suspicious cases; `benchmark.py` measures synthetic/local
query scenarios. Neither is an independent accuracy evaluation.
`reprocess.py` can recompute stored derived fields and skill rows in batches,
including remote restrictions. Its default invocation writes; inspect with
`--dry-run` first on a local database. Its `--source` choices currently cover the
original three ATS providers plus manual, not every implemented adapter.

If a matching change is separately authorized: preserve a reviewed baseline,
add meaningful regressions, version the change, evaluate before/after, and plan
reprocessing. Do not tune on the independent holdout before evaluating it.
