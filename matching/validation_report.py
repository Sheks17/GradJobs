"""Render measured validation results with explicit limitations and review guidance."""


def display(value):
    return "Unavailable" if value is None else f"{value:.1%}"


def render_report(report):
    uncategorized = report["uncategorized_classification_mistakes"]
    uncategorized_text = str(uncategorized) if report["human_labeled"] else "Unavailable"
    lines = [
        "# Phase 3 matching validation",
        "",
        f"Matching version: `{report['matching_version']}`. "
        f"Sample: **{report['sampled']} real postings**. "
        f"Human labeled: **{report['human_labeled']}**; unlabeled: **{report['unlabeled']}**.",
        "",
        "This report evaluates the frozen sample, not the live ingestion database. "
        "Predictions are "
        "recomputed from retained title/description using the current engine. Human "
        "labels are never generated.",
        "",
        "## Review workflow",
        "",
        "Open `data/evaluation/review.csv` in a spreadsheet using UTF-8 and text column types. "
        "Each row includes ID, title, company, role family, seniority, "
        "required/preferred bounds, "
        "score, confidence, excerpt, full description, source URL, location, and prediction. "
        "Experience bounds are `[minimum, maximum]`; `null` means unknown or unbounded, "
        "not zero.",
        "",
        "Fill only `human_label`, `reviewer_notes`, `reviewer`, and optional `error_categories`. "
        "Review the original wording before looking at the prediction to reduce anchoring. "
        "Use the retained full description as the review source; live URLs may change. "
        "Leave uncertain rows unlabeled and explain the uncertainty. Save as CSV without "
        "removing rows "
        "or changing IDs/content hashes. Rows may be sorted. Predictions and other "
        "spreadsheet fields "
        "are informational and are not imported into the engine.",
        "",
        "```powershell",
        "# Already exported; exporter refuses to overwrite an existing review file.",
        "python -m matching.review",
        "# Automatically reads review.csv beside the input dataset.",
        "python -m matching.evaluate --output data/evaluation/validation.json --markdown "
        "docs/phase3-validation.md",
        "```",
        "",
        "To compare a future justified rule change, save the first evaluation under a "
        "different output "
        "path before editing rules, then rerun against the same human labels afterward. "
        "`--reviews PATH` selects a separate review file; `--ignore-reviews` uses JSON "
        "labels only. "
        "CSV IDs, coverage, labels, error tags, and posting hashes are validated before "
        "any metrics are produced. "
        "The evaluator does not modify the CSV, JSON sample, or live jobs.",
        "",
        "## Labeling guidance",
        "",
        "These are guidelines, not absolute rules. Judge the overall requirements, not "
        "the current score.",
        "",
        "| Human label | Typical evidence |",
        "| --- | --- |",
        "| strong_fit | 0–2 years; explicit new graduate, entry, junior, associate; no "
        "experience required; recent graduates encouraged |",
        "| possible_fit | 1–3 years or unclear requirements; level I; otherwise "
        "accessible early in career |",
        "| stretch | Around 3 years or advanced requirements; plausible but not clearly "
        "for a new graduate |",
        "| not_early_career | 4+ years; senior/staff/principal/lead/manager; substantial "
        "leadership; experienced hire |",
        "",
        "Distinguish required experience from preferred experience, equivalent "
        "education, company history, "
        "and certification validity. Consider actual management duties rather than the "
        "word 'lead' alone. "
        "Internships and location eligibility warrant notes when they affect fit. The "
        "four labels describe "
        "career fit; tag role/location errors separately even when the career label "
        "happens to agree.",
        "",
        "## Measured results",
        "",
        f"Four-class accuracy: **{display(report['accuracy'])}**. Early-career precision: "
        f"**{display(report['early_career_precision'])}**; "
        f"recall: **{display(report['early_career_recall'])}**; "
        f"F1: **{display(report['early_career_f1'])}**.",
        "",
        "Early-career positives are human `strong_fit` or `possible_fit`. The current "
        "operational cutoff "
        "is 50. Four-class predictions use strong ≥70, possible ≥50, stretch ≥30, "
        "otherwise not early career. "
        "Precision is TP/(TP+FP), recall TP/(TP+FN), F1 2TP/(2TP+FP+FN). Undefined "
        "denominators yield null, "
        "not perfect accuracy. Full confusion matrix, row-level errors, and per-class "
        "metrics are in the JSON report.",
        "",
    ]
    if not report["human_labeled"]:
        lines += [
            "**No measured accuracy or failure patterns can be established yet.** Zero "
            "counts or empty "
            "error lists describe the absence of reviewed rows, not the absence of errors.",
            "",
        ]
    else:
        counts = report["early_career"]
        lines += [
            f"Labeled false positives: {counts['false_positives']}; "
            f"false negatives: {counts['false_negatives']}.",
            "",
        ]
    lines += [
        "## Threshold comparison",
        "",
        "Surfaced counts cover all sample rows; precision/recall/F1 use only labeled rows. "
        "The sample is stratified and not prevalence-weighted: these are not estimates "
        "of live database volume or precision.",
        "",
        "| Cutoff | Surfaced in sample | Surfaced labeled | Precision | Recall | F1 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["threshold_analysis"]:
        lines.append(
            f"| {row['threshold']} | {row['surfaced_in_sample']} | {row['surfaced_labeled']} | "
            f"{display(row['precision'])} | {display(row['recall'])} | {display(row['f1'])} |"
        )
    recommendation = report["threshold_recommendation"]
    lines += [
        "",
        (
            f"Provisional measured recommendation: **{recommendation['threshold']}**. "
            + recommendation["basis"]
        )
        if recommendation
        else "No measured threshold recommendation is available. Retain the existing **50** cutoff "
        "pending complete review; this is continuity, not a validated optimum. A provisional "
        "recommendation requires all rows labeled and both positive and negative examples. "
        "It maximizes F1 among the listed cutoffs, breaks ties toward recall, then the "
        "lower cutoff. "
        "It never automatically changes production settings.",
        "",
    ]
    for title, key in (
        ("Role family", "accuracy_by_role_family"),
        ("Experience category", "accuracy_by_experience_category"),
        ("Confidence calibration", "accuracy_by_confidence_band"),
    ):
        lines += [
            f"## {title}",
            "",
            "| Group | Sampled | Labeled | Accuracy |",
            "| --- | --- | --- | --- |",
        ]
        for row in report[key]:
            lines.append(
                f"| {row['group']} | {row['sampled']} | {row['labeled']} | "
                f"{display(row['accuracy'])} |"
            )
        lines.append("")
    lines += [
        "Confidence is currently an evidence-strength heuristic, not a probability. Compare the "
        "four-class accuracy of the four bands after review, accounting for small sample sizes "
        "and different role composition. No confidence logic has been changed in this "
        "validation. "
        "A reversal between bands is a prompt for investigation, not enough by itself to "
        "justify a rewrite.",
        "",
        "Confidence comparison status: "
        f"`{report['confidence_validation']['status']}`. The evaluator compares bands with "
        "at least five labeled rows; comparisons remain descriptive, not statistical proof.",
        "",
        "## Error analysis",
        "",
        "Enter semicolon-separated error tags after checking the posting. Counts below "
        "are reviewer "
        "assignments, can overlap, and include role/location issues even on correct "
        "career labels. "
        "Error causes are never automatically inferred from a classification mismatch.",
        "",
        "| Reviewer error category | Count |",
        "| --- | --- |",
    ]
    for category, count in report["reviewer_error_category_counts"].items():
        lines.append(f"| {category} | {count if count is not None else 'Unavailable'} |")
    lines += [
        "",
        f"Uncategorized classification mistakes: {uncategorized_text}.",
        "",
        "Diagnostics in JSON include predictions wrong at confidence ≥90; human not-early-career "
        "senior jobs scoring ≥70; human strong/possible jobs scoring <50; and role "
        "groups with ≥5 "
        "labels whose accuracy is over 15 percentage points below overall accuracy. These are "
        "review cues, not statistical significance tests. Most common failure modes cannot be "
        "ranked until reviewers supply labels and error tags.",
        "",
        "## Rules and before/after",
        "",
        "No scoring, role, experience, confidence, or threshold rules changed in this "
        "measurement task. "
        "There is no tuned before/after comparison. The 11,327-job reprocessing step is "
        "conditional on "
        "a justified rule change and was not repeated. IDs, source URLs, raw payloads, "
        "and discovery "
        "timestamps were not touched by this workflow.",
        "",
        "If reviewed errors justify a targeted change, first archive the before JSON, "
        "document the "
        "specific reviewed IDs and error pattern, change only the implicated rule, and run "
        "`python -m matching.reprocess --dry-run` then `python -m matching.reprocess`. "
        "Verify immutable "
        "fields against a backup and rerun evaluation on the same labels; never "
        "overwrite the before report.",
        "",
        "## Limitations and Phase 4 readiness",
        "",
        "Human review is still required before a matching-quality sign-off for provider "
        "expansion. "
        "The tooling is ready; accuracy readiness is not established by an unlabeled sample. "
        "Partial review can be selection-biased. Even complete review is a stratified sample of "
        "retained postings, not an independent population validation. Review "
        "disagreements should "
        "be adjudicated; threshold tuning on this sample requires an independent "
        "follow-up sample. "
        "Missing or ambiguous requirements should remain explicit. No new providers, "
        "authentication, "
        "AI classifier, or application UI were added.",
        "",
    ]
    return "\n".join(lines)
