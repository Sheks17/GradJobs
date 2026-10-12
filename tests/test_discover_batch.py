import csv

from collectors.discover_batch import discover_batch


def test_resume_preserves_verified_rows_and_empty_boards_remain_candidates(tmp_path, monkeypatch):
    import collectors.discover_batch as module

    path, output = tmp_path / "candidates.csv", tmp_path / "results.json"
    urls = ["https://example.com/good", "https://example.com/empty"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("careers_url", "company_name"))
        writer.writeheader()
        writer.writerows({"careers_url": url, "company_name": "Fixture"} for url in urls)
    calls = []

    def inspect(url):
        calls.append(url)
        return {
            "provider": "greenhouse",
            "board_token": "fixture",
            "verified": True,
            "jobs": int(url.endswith("good")),
        }

    monkeypatch.setattr(module, "discover", inspect)
    first = discover_batch(path, output)
    assert first[0]["stage"] == "verified" and first[0]["verified"]
    assert first[1]["stage"] == "provider_detected" and not first[1]["verified"]
    assert "no usable postings" in first[1]["reason"]
    assert discover_batch(path, output) == first and calls == urls
    discover_batch(path, output, retry=True)
    assert calls == urls + [urls[1]]
    assert all("enabled" not in row for row in first)
