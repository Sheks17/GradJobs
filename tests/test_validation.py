"""Evaluation arithmetic and review-file safety; fixture labels are not real-posting labels."""

import csv
from types import SimpleNamespace

import pytest

from matching.evaluate import confidence_comparison, evaluate
from matching.review import export_review, load_reviews
from matching.validation_report import render_report


@pytest.fixture
def sample():
    return {
        "jobs": [
            {
                "job_id": "one",
                "title": "Junior Developer",
                "description": "0-2 years required.",
                "company": "=UNTRUSTED()",
                "label": None,
            },
            {
                "job_id": "two",
                "title": "Senior Developer",
                "description": "5 years required.",
                "label": None,
            },
        ]
    }


def edit_csv(path, mutate):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_csv_roundtrip_preserves_blank_labels_and_recomputes_predictions(sample, tmp_path):
    path = tmp_path / "review.csv"
    assert export_review(sample, path) == 2
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["company"] == "'=UNTRUSTED()"
    assert all(not row["human_label"] for row in rows)
    assert rows[0]["full_description"] == sample["jobs"][0]["description"]
    assert evaluate(load_reviews(sample, path))["human_labeled"] == 0
    with pytest.raises(FileExistsError):
        export_review(sample, path)

    def reviewed(rows):
        rows.reverse()
        rows[0].update(human_label="not_early_career", early_career_score="100")
        rows[1].update(human_label="strong_fit", reviewer_notes="Read the required section")

    edit_csv(path, reviewed)
    reviewed_dataset = load_reviews(sample, path)
    assert sample["jobs"][0]["label"] is None  # No mutation of original data.
    assert reviewed_dataset["jobs"][0]["notes"] == "Read the required section"
    report = evaluate(reviewed_dataset)
    assert report["accuracy"] == 1
    assert report["early_career_precision"] == report["early_career_recall"] == 1
    assert report["predicted_vs_actual"][1]["score"] < 50


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows[0].update(human_label="generated_guess"),
        lambda rows: rows[0].update(content_hash="changed"),
        lambda rows: rows[0].update(job_id="unknown"),
        lambda rows: rows[0].update(job_id=rows[1]["job_id"]),
        lambda rows: rows.pop(),
        lambda rows: rows[0].update(human_label="strong_fit", error_categories="invented"),
        lambda rows: rows[0].update(error_categories="experience_parser"),
    ],
)
def test_invalid_review_fails_closed(sample, tmp_path, mutation):
    path = tmp_path / "review.csv"
    export_review(sample, path)
    edit_csv(path, mutation)
    with pytest.raises(ValueError):
        load_reviews(sample, path)


def test_review_cannot_silently_erase_existing_label(sample, tmp_path):
    path = tmp_path / "review.csv"
    export_review(sample, path)
    sample["jobs"][0]["label"] = "strong_fit"
    with pytest.raises(ValueError, match="Conflicting"):
        load_reviews(sample, path)


def test_metrics_thresholds_and_diagnostics(monkeypatch):
    # These deliberate fixture errors test arithmetic, not measured product accuracy.
    scores = {"tp": (80, 95), "fp": (70, 95), "fn": (40, 60), "tn": (10, 40)}

    def score(title, description):
        value, confidence = scores[title]
        return SimpleNamespace(
            early_career_score=value,
            classification_confidence=confidence,
            role_family="Software Engineering",
            experience_category="0_2",
            seniority_level="senior" if title == "fp" else "entry",
        )

    monkeypatch.setattr("matching.evaluate.score_job", score)
    jobs = [
        {
            "job_id": name,
            "title": name,
            "description": "fixture",
            "label": label,
            "error_categories": tags,
        }
        for name, label, tags in [
            ("tp", "strong_fit", []),
            ("fp", "not_early_career", ["seniority_title"]),
            ("fn", "possible_fit", ["experience_parser", "preferred_vs_required"]),
            ("tn", "not_early_career", []),
        ]
    ]
    report = evaluate({"jobs": jobs})
    assert report["human_labeled"] == 4
    assert report["accuracy"] == 0.5
    assert report["early_career_precision"] == report["early_career_recall"] == 0.5
    assert report["early_career_f1"] == 0.5
    assert report["early_career"]["false_positives"] == 1
    assert report["early_career"]["false_negatives"] == 1
    threshold = next(row for row in report["threshold_analysis"] if row["threshold"] == 75)
    assert threshold["precision"] == 1 and threshold["recall"] == 0.5
    assert threshold["surfaced_in_sample"] == 1 and threshold["f1"] == pytest.approx(2 / 3)
    assert report["threshold_recommendation"]["threshold"] == 75
    assert [row["job_id"] for row in report["high_confidence_wrong"]] == ["fp"]
    assert [row["job_id"] for row in report["senior_jobs_ranked_high"]] == ["fp"]
    assert [row["job_id"] for row in report["valid_entry_jobs_ranked_low"]] == ["fn"]
    assert report["reviewer_error_category_counts"]["experience_parser"] == 1
    assert report["accuracy_by_confidence_band"][0]["accuracy"] == 0.5
    assert report["accuracy_by_confidence_band"][1]["accuracy"] is None
    # Partial review must not recommend a production cutoff from selected labels.
    jobs[3]["label"] = None
    assert evaluate({"jobs": jobs})["threshold_recommendation"] is None


def test_zero_labels_report_no_accuracy_or_recommendation(sample):
    report = evaluate(sample)
    assert report["threshold_recommendation"] is None
    assert all(row["accuracy"] is None for row in report["accuracy_by_confidence_band"])
    assert all(value is None for value in report["reviewer_error_category_counts"].values())
    rendered = render_report(report)
    assert "No measured accuracy" in rendered
    assert "Unavailable" in rendered


def test_confidence_reversal_is_reported_without_claiming_calibration():
    result = confidence_comparison(
        [
            {"group": "90+", "labeled": 5, "accuracy": 0.6},
            {"group": "75–89", "labeled": 6, "accuracy": 0.9},
            {"group": "50–74", "labeled": 1, "accuracy": 1},
            {"group": "below 50", "labeled": 0, "accuracy": None},
        ]
    )
    assert result["status"] == "observed_comparisons"
    assert len(result["comparisons"]) == 1
    assert result["comparisons"][0]["higher_band_less_accurate"] is True


def test_changed_posting_invalidates_previous_review(sample, tmp_path):
    path = tmp_path / "review.csv"
    export_review(sample, path)
    sample["jobs"][0]["description"] = "Now requires 5 years"
    with pytest.raises(ValueError, match="does not match"):
        load_reviews(sample, path)


def test_existing_error_tags_roundtrip(sample, tmp_path):
    sample["jobs"][0].update(label="strong_fit", error_categories=["location", "role_family"])
    path = tmp_path / "review.csv"
    export_review(sample, path)
    assert load_reviews(sample, path)["jobs"][0]["error_categories"] == ["location", "role_family"]


@pytest.mark.parametrize("malformation", ["duplicate_header", "extra_cell"])
def test_malformed_csv_is_rejected(sample, tmp_path, malformation):
    path = tmp_path / "review.csv"
    export_review(sample, path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    if malformation == "duplicate_header":
        rows[0][1] = rows[0][0]
    else:
        rows[1].append("extra")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerows(rows)
    with pytest.raises(ValueError):
        load_reviews(sample, path)
