import pytest

from collectors.normalizers.location import location_fields
from collectors.normalizers.text import (
    normalize_company,
    normalize_title,
    normalize_url,
    plain_text,
)


@pytest.mark.parametrize(
    "value,expected",
    [(" ACME, Inc. ", "acme"), ("Example LLC", "example"), ("The Company", "the company")],
)
def test_company(value, expected):
    assert normalize_company(value) == expected


def test_title():
    assert normalize_title(" Sr. Software Engineer ") == "senior software engineer"
    assert normalize_title("Jr. Front-End Developer") == "junior front end developer"
    assert normalize_title("C++ Engineer I") != normalize_title("C# Engineer II")


def test_url_preserves_requisition():
    assert (
        normalize_url("https://EXAMPLE.com/jobs/?gh_jid=23&utm_source=x#apply")
        == "https://example.com/jobs?gh_jid=23"
    )
    assert normalize_url("https://example.com/?id=1") != normalize_url("https://example.com/?id=2")


def test_html_is_text():
    assert (
        plain_text("&amp;lt;p&amp;gt;Hello&amp;lt;/p&amp;gt;<script>alert(1)</script>") == "Hello"
    )


def test_location_does_not_assume_remote_means_us():
    assert location_fields("Remote")["country"] is None
    assert location_fields("Remote - work with us")["country"] is None
    assert location_fields("Remote, United States")["country"] == "US"
    assert location_fields("Austin, TX")["state"] == "TX"
    assert location_fields("Toronto, Canada")["country"] == "CA"
    assert location_fields("Remote", country="Canada")["country"] == "CA"
    assert location_fields("London", "OnSite")["remote_type"] == "onsite"
