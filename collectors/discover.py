"""Bounded, public-page ATS discovery. Never guesses a board from a company name."""

import argparse
import ipaddress
import re
import socket
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from collectors.ats_registry import ATS_REGISTRY, capability, detect_url
from collectors.providers import PROVIDERS
from collectors.workday import WorkdayCollector, source_token, workday_config
from services.api.app.core.config import get_settings


def ats_from_url(url: str) -> tuple[str, str] | None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        token = (
            parse_qs(parsed.query).get("for", [None])[0]
            if parts[:1] == ["embed"]
            else (parts[0] if parts else None)
        )
        provider = "greenhouse"
    elif host == "jobs.lever.co":
        token, provider = (parts[0] if parts else None), "lever"
    elif host == "jobs.ashbyhq.com":
        token, provider = (parts[0] if parts else None), "ashby"
    elif host in {
        "careers.smartrecruiters.com",
        "jobs.smartrecruiters.com",
        "www.smartrecruiters.com",
    }:
        token, provider = (parts[0] if parts else None), "smartrecruiters"
    elif host == "apply.workable.com":
        token, provider = (parts[0] if parts and parts[0] not in {"j", "api"} else None), "workable"
    elif detect_url(url) in {"recruitee", "breezyhr"}:
        token, provider = host.split(".")[0], detect_url(url)
    else:
        return None
    return (provider, token) if token and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", token) else None


def public_url(url: str) -> None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        raise ValueError("LinkedIn fetching is disabled")
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 80, 443}
    ):
        raise ValueError("Only public HTTP(S) URLs without credentials are allowed")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Private or local network addresses are not supported")


def fetch_page(client: httpx.Client, url: str, check_robots: bool = False) -> tuple[str, str]:
    for _ in range(6):
        public_url(url)
        if check_robots:
            check_allowed(client, url)
        with client.stream("GET", url) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 2_000_000:
                    raise ValueError("Discovery page exceeds 2 MB limit")
            return url, data.decode("utf-8", errors="replace")
    raise ValueError("Too many redirects")


def check_allowed(client: httpx.Client, url: str) -> None:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        _, robots = fetch_page(client, robots_url)
        parser = RobotFileParser()
        parser.parse(robots.splitlines())
        if not parser.can_fetch("GradJobs", url):
            raise ValueError("robots.txt disallows discovery on this page")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise


def allowed_page(client: httpx.Client, url: str) -> tuple[str, str]:
    return fetch_page(client, url, check_robots=True)


def page_candidates(url: str, html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links = [url]
    links.extend(
        urljoin(url, node.get("href") or node.get("src") or node.get("content") or "")
        for node in soup.select("a[href], iframe[src], meta[content]")
    )
    # Public embedded JSON often contains an explicit ATS URL rather than an anchor.
    links.extend(
        re.findall(
            r"https://[A-Za-z0-9.-]+/[A-Za-z0-9_/?=&%-]*",
            html.replace("\\/", "/"),
        )
    )
    return list(dict.fromkeys(candidate for link in links if (candidate := ats_from_url(link))))


def _discover(url: str) -> dict:
    url = url if "://" in url else "https://" + url
    if (urlsplit(url).hostname or "").endswith(".myworkdayjobs.com"):
        try:
            config = workday_config(url)
            collector = WorkdayCollector(source_token(config), config["tenant"], config=config)
            try:
                # Discovery verifies pagination and one detail, rather than downloading
                # thousands of descriptions solely to identify a career board.
                first = collector.request_json(
                    "POST",
                    url=collector.endpoint + "/jobs",
                    json={
                        "limit": 20,
                        "offset": 0,
                        "searchText": "",
                        "appliedFacets": {},
                    },
                )
                listings = first.get("jobPostings")
                total = first.get("total")
                if (
                    not isinstance(total, int)
                    or total < 1
                    or not isinstance(listings, list)
                    or not listings
                ):
                    raise ValueError("No visible Workday jobs")
                listing = listings[0]
                path = listing.get("externalPath", "")
                if not path.startswith("/job/") or ".." in path:
                    raise ValueError("Invalid Workday job path")
                detail = collector.get_json(url=collector.endpoint + path)
                collector.normalize({"listing": listing, "detail": detail})
                if total > len(listings):
                    second = collector.request_json(
                        "POST",
                        url=collector.endpoint + "/jobs",
                        json={
                            "limit": 20,
                            "offset": len(listings),
                            "searchText": "",
                            "appliedFacets": {},
                        },
                    )
                    if not second.get("jobPostings") or second["jobPostings"][0] == listing:
                        raise ValueError("Workday pagination could not be verified")
                return {
                    "provider": "workday",
                    "board_token": source_token(config),
                    "provider_config": config,
                    "verified": True,
                    "jobs": total,
                    "verification_scope": "list, pagination and first detail",
                }
            finally:
                collector.close()
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return {"provider": "workday", "verified": False, "reason": type(exc).__name__}
    candidates = []
    direct = ats_from_url(url)
    if direct:
        candidates.append(direct)
    else:
        with httpx.Client(
            timeout=20,
            follow_redirects=False,
            headers={"User-Agent": get_settings().collector_user_agent},
        ) as client:
            final_url, html = allowed_page(client, url)
            soup = BeautifulSoup(html, "html.parser")
            workday_links = [
                urljoin(final_url, node.get("href") or node.get("src") or "")
                for node in soup.select("a[href], iframe[src]")
            ]
            if (urlsplit(final_url).hostname or "").endswith(".myworkdayjobs.com"):
                workday_links.insert(0, final_url)
            for link in workday_links:
                if (urlsplit(link).hostname or "").endswith(".myworkdayjobs.com"):
                    result = discover(link)
                    if result["verified"]:
                        return result
            candidates.extend(page_candidates(final_url, html))
            if not candidates:
                detected = detected_page(final_url, html)
                if detected:
                    return detected
            if not candidates:
                soup = BeautifulSoup(html, "html.parser")
                career_links = list(
                    dict.fromkeys(
                        urljoin(final_url, node["href"])
                        for node in soup.select("a[href]")
                        if re.search(
                            r"careers?|jobs|join (?:us|our team)",
                            node.get_text(" ") + " " + node["href"],
                            re.I,
                        )
                        and urlsplit(urljoin(final_url, node["href"])).netloc
                        == urlsplit(final_url).netloc
                    )
                )
                # Follow at most two observed same-site careers links; no guessed paths.
                for link in career_links[:2]:
                    if link == final_url:
                        continue
                    try:
                        page_url, page = allowed_page(client, link)
                        candidates.extend(page_candidates(page_url, page))
                        if not candidates and (detected := detected_page(page_url, page)):
                            return detected
                    except (httpx.HTTPError, ValueError):
                        continue
                    if candidates:
                        break
    verified = []
    for provider, board in candidates[:5]:
        collector = PROVIDERS[provider](board, board)
        try:
            jobs = collector.fetch()
            if not getattr(collector, "snapshot_complete", True):
                raise ValueError("Incomplete public snapshot")
            if provider in {"workable", "recruitee", "breezyhr"}:
                for job in jobs:
                    collector.normalize(job)
            verified.append(
                {"provider": provider, "board_token": board, "verified": True, "jobs": len(jobs)}
            )
        except (httpx.HTTPError, ValueError):
            continue
        finally:
            collector.close()
    return (
        {
            "provider": candidates[0][0] if candidates else "unknown",
            "verified": False,
            "reason": "Endpoint verification failed" if candidates else "No reliable ATS evidence",
        }
        if not verified
        else {**verified[0], "candidates": verified}
    )


def detected_page(url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = [url] + [
        urljoin(url, node.get("href") or node.get("src") or "")
        for node in soup.select("a[href],iframe[src]")
    ]
    links.extend(
        re.findall(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9_/?=&%-]*", html.replace("\\/", "/"))
    )
    for link in links[:500]:
        provider = detect_url(link)
        if provider:
            return {
                **capability(provider),
                "verified": False,
                "observed_careers_url": link,
                "reason": "Observed ATS URL; no usable endpoint verified",
            }
    # A LinkedIn profile/apply/social link or mention of an integration is not
    # evidence that this careers site is powered by Talent Hub.
    generator = soup.find("meta", attrs={"name": "generator"})
    if generator:
        value = generator.get("content", "").casefold().strip()
        for provider, item in ATS_REGISTRY.items():
            if value in {name.casefold() for name in [item["canonical_name"], *item["aliases"]]}:
                return {
                    **capability(provider),
                    "verified": False,
                    "detection_confidence": "medium"
                    if provider == "linkedin_talent_hub"
                    else "high",
                    "reason": "Observed generator metadata; no account identifier guessed",
                }
    return None


def discover(url: str) -> dict:
    url = url if "://" in url else "https://" + url
    host = (urlsplit(url).hostname or "").lower()
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return {
            "provider": "unknown",
            "verified": False,
            "reason": "LinkedIn fetching is disabled; a URL cannot identify Talent Hub",
        }
    detected = detect_url(url)
    if detected and detected not in PROVIDERS:
        return {**capability(detected), "verified": False, "observed_careers_url": url}
    result = _discover(url)
    if result["provider"] == "unknown" and detected:
        result.update(provider=detected, reason="Observed ATS URL; account/endpoint not verified")
    provider = result["provider"]
    return {**(capability(provider) if provider in ATS_REGISTRY else {}), **result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        result = discover(args.url)
        print(f"Provider: {result['provider']}\nVerified: {str(result['verified']).lower()}")
        if result.get("board_token"):
            print(f"Board token: {result['board_token']}")
        for key, label in (
            ("detection_confidence", "Detection confidence"),
            ("public_ingestion", "Public ingestion"),
            ("access_classification", "Access classification"),
            ("jobs", "Visible jobs"),
            ("unsupported_reason", "Reason"),
        ):
            if result.get(key) is not None:
                print(f"{label}: {result[key]}")
    except (ValueError, httpx.HTTPError, OSError) as exc:
        print(f"Provider: unknown\nVerified: false\nReason: {type(exc).__name__}")
        raise SystemExit(1) from None
