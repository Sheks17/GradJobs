# Phase 3 matching validation

Matching version: `3.0.0`. Sample: **220 real postings**. Human labeled: **220**; unlabeled: **0**.

This report evaluates the frozen sample, not the live ingestion database. Predictions are recomputed from retained title/description using the current engine. Human labels are never generated.

## Review workflow

Open `data/evaluation/gradjobs_review_draft_labeled.csv` in a spreadsheet using UTF-8 and text column types. Each row includes ID, title, company, role family, seniority, required/preferred bounds, score, confidence, excerpt, full description, source URL, location, and prediction. Experience bounds are `[minimum, maximum]`; `null` means unknown or unbounded, not zero.

Fill only `human_label`, `reviewer_notes`, `reviewer`, and optional `error_categories`. Review the original wording before looking at the prediction to reduce anchoring. Use the retained full description as the review source; live URLs may change. Leave uncertain rows unlabeled and explain the uncertainty. Save as CSV without removing rows or changing IDs/content hashes. Rows may be sorted. Predictions and other spreadsheet fields are informational and are not imported into the engine.

```powershell
# Use the renamed, human-approved review CSV explicitly.
python -m matching.evaluate --reviews data/evaluation/gradjobs_review_draft_labeled.csv --output data/evaluation/validation.json --markdown docs/phase3-validation.md
```

To compare a future justified rule change, save the first evaluation under a different output path before editing rules, then rerun against the same human labels afterward. `--reviews PATH` selects a separate review file; `--ignore-reviews` uses JSON labels only. CSV IDs, coverage, labels, error tags, and posting hashes are validated before any metrics are produced. The evaluator does not modify the CSV, JSON sample, or live jobs.

## Labeling guidance

These are guidelines, not absolute rules. Judge the overall requirements, not the current score.

| Human label | Typical evidence |
| --- | --- |
| strong_fit | 0–2 years; explicit new graduate, entry, junior, associate; no experience required; recent graduates encouraged |
| possible_fit | 1–3 years or unclear requirements; level I; otherwise accessible early in career |
| stretch | Around 3 years or advanced requirements; plausible but not clearly for a new graduate |
| not_early_career | 4+ years; senior/staff/principal/lead/manager; substantial leadership; experienced hire |

Distinguish required experience from preferred experience, equivalent education, company history, and certification validity. Consider actual management duties rather than the word 'lead' alone. Internships and location eligibility warrant notes when they affect fit. The four labels describe career fit; tag role/location errors separately even when the career label happens to agree.

## Measured results

Four-class accuracy: **99.1%**. Early-career precision: **100.0%**; recall: **98.7%**; F1: **99.4%**.

Early-career positives are human `strong_fit` or `possible_fit`. The current operational cutoff is 50. Four-class predictions use strong ≥70, possible ≥50, stretch ≥30, otherwise not early career. Precision is TP/(TP+FP), recall TP/(TP+FN), F1 2TP/(2TP+FP+FN). Undefined denominators yield null, not perfect accuracy. Full confusion matrix, row-level errors, and per-class metrics are in the JSON report.

Labeled false positives: 0; false negatives: 1.

## Threshold comparison

Surfaced counts cover all sample rows; precision/recall/F1 use only labeled rows. The sample is stratified and not prevalence-weighted: these are not estimates of live database volume or precision.

| Cutoff | Surfaced in sample | Surfaced labeled | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- |
| 50 | 78 | 78 | 100.0% | 98.7% | 99.4% |
| 60 | 45 | 45 | 100.0% | 57.0% | 72.6% |
| 65 | 45 | 45 | 100.0% | 57.0% | 72.6% |
| 70 | 37 | 37 | 100.0% | 46.8% | 63.8% |
| 75 | 30 | 30 | 100.0% | 38.0% | 55.0% |
| 80 | 16 | 16 | 100.0% | 20.3% | 33.7% |

Provisional measured recommendation: **50**. Maximum sample F1; ties favor recall, then lower threshold. Confirm on an independent sample before changing production.

## Role family

| Group | Sampled | Labeled | Accuracy |
| --- | --- | --- | --- |
| Application Support | 1 | 1 | 100.0% |
| Back-End | 8 | 8 | 100.0% |
| Cloud / Infrastructure | 7 | 7 | 100.0% |
| Cybersecurity | 6 | 6 | 100.0% |
| Data / Analytics | 8 | 8 | 100.0% |
| Database | 6 | 6 | 100.0% |
| DevOps / SRE | 6 | 6 | 100.0% |
| Front-End | 6 | 6 | 83.3% |
| Full-Stack | 6 | 6 | 100.0% |
| IT Support | 6 | 6 | 100.0% |
| Implementation | 7 | 7 | 100.0% |
| Mobile | 6 | 6 | 100.0% |
| Networking | 6 | 6 | 100.0% |
| Other | 92 | 92 | 98.9% |
| Product Support | 6 | 6 | 100.0% |
| QA / Testing | 6 | 6 | 100.0% |
| Software Engineering | 19 | 19 | 100.0% |
| Solutions Engineering | 6 | 6 | 100.0% |
| Systems / Business Systems | 6 | 6 | 100.0% |
| Technical Support | 6 | 6 | 100.0% |

## Experience category

| Group | Sampled | Labeled | Accuracy |
| --- | --- | --- | --- |
| 0_2 | 20 | 20 | 95.0% |
| 1_2 | 2 | 2 | 100.0% |
| 1_3 | 2 | 2 | 100.0% |
| 3_plus | 13 | 13 | 92.3% |
| 4_plus | 10 | 10 | 100.0% |
| 5_plus | 76 | 76 | 100.0% |
| ambiguous | 5 | 5 | 100.0% |
| no_experience_required | 8 | 8 | 100.0% |
| unspecified | 84 | 84 | 100.0% |

## Confidence calibration

| Group | Sampled | Labeled | Accuracy |
| --- | --- | --- | --- |
| 90+ | 70 | 70 | 100.0% |
| 75–89 | 57 | 57 | 98.2% |
| 50–74 | 78 | 78 | 98.7% |
| below 50 | 15 | 15 | 100.0% |

Confidence is currently an evidence-strength heuristic, not a probability. Compare the four-class accuracy of the four bands after review, accounting for small sample sizes and different role composition. No confidence logic has been changed in this validation. A reversal between bands is a prompt for investigation, not enough by itself to justify a rewrite.

Confidence comparison status: `observed_comparisons`. The evaluator compares bands with at least five labeled rows; comparisons remain descriptive, not statistical proof.

## Error analysis

Enter semicolon-separated error tags after checking the posting. Counts below are reviewer assignments, can overlap, and include role/location issues even on correct career labels. Error causes are never automatically inferred from a classification mismatch.

| Reviewer error category | Count |
| --- | --- |
| experience_parser | 0 |
| seniority_title | 0 |
| role_family | 0 |
| misleading_title | 0 |
| education_equivalency | 0 |
| preferred_vs_required | 0 |
| description_ambiguity | 0 |
| internship_wording | 0 |
| management_wording | 0 |
| location | 0 |

Uncategorized classification mistakes: 2.

Diagnostics in JSON include predictions wrong at confidence ≥90; human not-early-career senior jobs scoring ≥70; human strong/possible jobs scoring <50; and role groups with ≥5 labels whose accuracy is over 15 percentage points below overall accuracy. These are review cues, not statistical significance tests. Two classification mismatches were observed: an Engineer III / 3-year posting labeled stretch but predicted not early career, and Associate Product Manager labeled strong fit but predicted not early career. Error-category tags are blank; zero category counts mean no causes were tagged, not that no errors occurred. These isolated cases do not establish a common systematic failure mode.

## Rules and before/after

No scoring, role, experience, confidence, or threshold rules changed in this measurement task. There is no tuned before/after comparison. The 11,327-job reprocessing step is conditional on a justified rule change and was not repeated. IDs, source URLs, raw payloads, and discovery timestamps were not touched by this workflow.

If reviewed errors justify a targeted change, first archive the before JSON, document the specific reviewed IDs and error pattern, change only the implicated rule, and run `python -m matching.reprocess --dry-run` then `python -m matching.reprocess`. Verify immutable fields against a backup and rerun evaluation on the same labels; never overwrite the before report.

## Limitations and Phase 4 readiness

All 220 labels are human-approved. This sample supports retaining cutoff 50 and proceeding to a limited Phase 4 pilot with continuing quality review; it does not establish population-wide accuracy. Independent labeling of a fresh sample is recommended before broad expansion. Partial review can be selection-biased. Even complete review is a stratified sample of retained postings, not an independent population validation. Review disagreements should be adjudicated; threshold tuning on this sample requires an independent follow-up sample. Missing or ambiguous requirements should remain explicit. No new providers, authentication, AI classifier, or application UI were added.

## Human review confirmation (2026-10-10)

The user confirmed: "I reviewed them myself they are good." All 220 draft labels were personally reviewed and approved. The original CSV still identifies its draft origin as `ChatGPT-draft`; labels and notes were preserved. Confirmation is recorded in `data/evaluation/review-confirmation.json` and the current JSON report. This is human-approved, AI-assisted annotation, not a blinded independent labeling exercise; anchoring may inflate agreement.

No scoring or confidence rules changed in this run. Confidence-band accuracies are 100% (90+), 98.2% (75–89), 98.7% (50–74), and 100% (below 50). The small reversals involve only two classification mistakes and do not justify recalibrating the heuristic. Front-End accuracy is 5/6; one mismatch is insufficient evidence of a systematic role-family problem. No high-confidence wrong predictions or senior jobs ranked highly were found among these reviewed rows.

The two observed mistakes remain uncategorized by the reviewer. Further adjudication should distinguish whether the manager-title case concerns career fit versus the product scope of supported technology role families. No live jobs were reprocessed and no before/after tuning claim is made. This run regenerated evaluation artifacts only; the earlier code-test results are unchanged. Regeneration replaces this manual confirmation section; retain the confirmation sidecar as provenance.
