"""Report accuracy only for manually labeled real postings; never create labels."""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from matching.aliases import SENIOR_LEVELS
from matching.review import ERROR_CATEGORIES, fingerprint, load_reviews
from matching.sample_evaluation import LABELS
from matching.scoring import MATCHING_VERSION, score_job


def prediction(score):
    return (
        "strong_fit"
        if score >= 70
        else "possible_fit"
        if score >= 50
        else "stretch"
        if score >= 30
        else "not_early_career"
    )


POSITIVE_LABELS = {"strong_fit", "possible_fit"}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def binary_metrics(rows, threshold):
    tp = sum(r["label"] in POSITIVE_LABELS and r["score"] >= threshold for r in rows)
    fp = sum(r["label"] not in POSITIVE_LABELS and r["score"] >= threshold for r in rows)
    fn = sum(r["label"] in POSITIVE_LABELS and r["score"] < threshold for r in rows)
    tn = len(rows) - tp - fp - fn
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


def grouped_accuracy(rows, key, groups=None):
    output = []
    for name in groups if groups is not None else sorted({row[key] for row in rows}):
        group = [row for row in rows if row[key] == name]
        labeled = [row for row in group if row["label"]]
        output.append(
            {
                "group": name,
                "sampled": len(group),
                "labeled": len(labeled),
                "accuracy": ratio(
                    sum(r["label"] == r["prediction"] for r in labeled), len(labeled)
                ),
            }
        )
    return output


def confidence_band(confidence):
    return (
        "90+"
        if confidence >= 90
        else "75–89"
        if confidence >= 75
        else "50–74"
        if confidence >= 50
        else "below 50"
    )


def confidence_comparison(bands):
    supported = [band for band in bands if band["labeled"] >= 5]
    comparisons = [
        {
            "higher_band": higher["group"],
            "lower_band": lower["group"],
            "higher_accuracy": higher["accuracy"],
            "lower_accuracy": lower["accuracy"],
            "higher_band_less_accurate": higher["accuracy"] < lower["accuracy"],
        }
        for higher, lower in zip(supported, supported[1:], strict=False)
    ]
    return {
        "status": "observed_comparisons" if comparisons else "insufficient_labeled_bands",
        "minimum_labels_per_band": 5,
        "comparisons": comparisons,
        "note": "Descriptive comparisons only; small samples and role mix may explain reversals.",
    }


def evaluate(dataset):
    rows = []
    for job in dataset["jobs"]:
        label = job.get("label")
        if label and label not in LABELS:
            raise ValueError(f"Invalid human label for {job['job_id']}: {label}")
        result = score_job(job["title"], job["description"])
        categories = job.get("error_categories", [])
        if isinstance(categories, str):
            categories = [value.strip() for value in categories.split(";") if value.strip()]
        if set(categories) - set(ERROR_CATEGORIES):
            raise ValueError(f"Invalid error categories for {job['job_id']}")
        rows.append(
            {
                "job_id": job["job_id"],
                "title": job["title"],
                "label": label or None,
                "prediction": prediction(result.early_career_score),
                "score": result.early_career_score,
                "confidence": result.classification_confidence,
                "role_family": result.role_family,
                "experience_category": result.experience_category,
                "confidence_band": confidence_band(result.classification_confidence),
                "seniority": result.seniority_level,
                "error_categories": categories,
                "reviewer_notes": job.get("notes", ""),
                "content_hash": fingerprint(job),
            }
        )
    labeled = [row for row in rows if row["label"]]
    matrix = Counter((row["label"], row["prediction"]) for row in labeled)
    accuracy = ratio(
        sum(a == b for a, b in [(r["label"], r["prediction"]) for r in labeled]), len(labeled)
    )
    binary = binary_metrics(labeled, 50)
    thresholds = [
        {
            "threshold": threshold,
            "surfaced_in_sample": sum(r["score"] >= threshold for r in rows),
            "surfaced_labeled": sum(r["score"] >= threshold for r in labeled),
            **binary_metrics(labeled, threshold),
        }
        for threshold in (50, 60, 65, 70, 75, 80)
    ]
    per_class = []
    for label in LABELS:
        tp = matrix[(label, label)]
        fp = sum(
            n for (human, predicted), n in matrix.items() if predicted == label and human != label
        )
        fn = sum(
            n for (human, predicted), n in matrix.items() if human == label and predicted != label
        )
        per_class.append(
            {
                "label": label,
                "support": sum(r["label"] == label for r in labeled),
                "precision": ratio(tp, tp + fp),
                "recall": ratio(tp, tp + fn),
                "f1": ratio(2 * tp, 2 * tp + fp + fn),
                "false_positives": fp,
                "false_negatives": fn,
            }
        )
    mistakes = [r for r in labeled if r["label"] != r["prediction"]]
    category_counts = Counter(
        category for row in labeled for category in set(row["error_categories"])
    )
    roles = grouped_accuracy(rows, "role_family")
    confidence_bands = grouped_accuracy(
        rows, "confidence_band", ["90+", "75–89", "50–74", "below 50"]
    )
    recommendation = None
    # Require complete review and both positive and negative examples for a provisional comparison.
    if (
        len(labeled) == len(rows)
        and labeled
        and 0 < sum(r["label"] in POSITIVE_LABELS for r in labeled) < len(labeled)
    ):
        best = max(
            thresholds, key=lambda row: (row["f1"] or 0, row["recall"] or 0, -row["threshold"])
        )
        recommendation = {
            "threshold": best["threshold"],
            "status": "provisional",
            "basis": (
                "Maximum sample F1; ties favor recall, then lower threshold. "
                "Confirm on an independent sample before changing production."
            ),
        }
    return {
        "matching_version": MATCHING_VERSION,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "sampled": len(rows),
        "human_labeled": len(labeled),
        "unlabeled": len(rows) - len(labeled),
        "accuracy": accuracy,
        "early_career_precision": binary["precision"],
        "early_career_recall": binary["recall"],
        "early_career_f1": binary["f1"],
        "early_career": binary,
        "class_metrics": per_class,
        "confusion_matrix": [
            {"human_label": a, "prediction": b, "count": n} for (a, b), n in sorted(matrix.items())
        ],
        "predicted_vs_actual": labeled,
        "threshold_analysis": thresholds,
        "threshold_recommendation": recommendation,
        "operational_threshold": 50,
        "accuracy_by_role_family": roles,
        "accuracy_by_experience_category": grouped_accuracy(rows, "experience_category"),
        "accuracy_by_confidence_band": confidence_bands,
        "confidence_validation": confidence_comparison(confidence_bands),
        "high_confidence_wrong": [r for r in mistakes if r["confidence"] >= 90],
        "senior_jobs_ranked_high": [
            r
            for r in labeled
            if r["seniority"] in SENIOR_LEVELS
            and r["label"] == "not_early_career"
            and r["score"] >= 70
        ],
        "valid_entry_jobs_ranked_low": [
            r for r in labeled if r["label"] in POSITIVE_LABELS and r["score"] < 50
        ],
        "poor_role_families": [
            r for r in roles if r["labeled"] >= 5 and r["accuracy"] < (accuracy or 0) - 0.15
        ],
        "reviewer_error_category_counts": {
            category: category_counts[category] if labeled else None
            for category in ERROR_CATEGORIES
        },
        "uncategorized_classification_mistakes": sum(
            not row["error_categories"] for row in mistakes
        )
        if labeled
        else None,
        "note": (
            "Metrics apply only to human-labeled rows; "
            "this stratified sample is not prevalence-weighted. Confidence is evidence "
            "strength, not a probability. "
            "Error causes require reviewer tags, never inferred automatically. Empty "
            "diagnostic lists with zero labels are not evidence of zero errors."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/evaluation/jobs.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path, help="Write the human-readable validation report")
    parser.add_argument(
        "--reviews", type=Path, help="CSV from matching.review; auto-detected beside input"
    )
    parser.add_argument("--ignore-reviews", action="store_true", help="Use JSON human labels only")
    args = parser.parse_args()
    dataset = json.loads(args.input.read_text(encoding="utf-8"))
    if args.ignore_reviews and args.reviews:
        parser.error("--reviews and --ignore-reviews cannot be combined")
    review_path = args.reviews or args.input.with_name("review.csv")
    try:
        if not args.ignore_reviews and (args.reviews or review_path.exists()):
            dataset = load_reviews(dataset, review_path)
        result = evaluate(dataset)
    except ValueError as exc:
        parser.error(str(exc))
    result["review_source"] = (
        str(review_path) if not args.ignore_reviews and review_path.exists() else str(args.input)
    )
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown:
        from matching.validation_report import render_report

        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_report(result), encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
