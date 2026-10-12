"""Bounded, public-page ATS discovery. Never guesses a board from a company name."""

import argparse
import ipaddress
import re
import socket
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from collectors.providers import PROVIDERS
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
    else:
        return None
    return (provider, token) if token and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", token) else None


def public_url(url: str) -> None:
    parsed = urlsplit(url)
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
            r"https://(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io|jobs\.lever\.co|jobs\.ashbyhq\.com|careers\.smartrecruiters\.com|jobs\.smartrecruiters\.com|www\.smartrecruiters\.com)/[A-Za-z0-9_/?=&-]+",
            html.replace("\\/", "/"),
        )
    )
    return list(dict.fromkeys(candidate for link in links if (candidate := ats_from_url(link))))


def discover(url: str) -> dict:
    url = url if "://" in url else "https://" + url
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
            candidates.extend(page_candidates(final_url, html))
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
                    except (httpx.HTTPError, ValueError):
                        continue
                    if candidates:
                        break
    verified = []
    for provider, board in candidates[:5]:
        collector = PROVIDERS[provider](board, board)
        try:
            jobs = collector.fetch()
            verified.append(
                {"provider": provider, "board_token": board, "verified": True, "jobs": len(jobs)}
            )
        except (httpx.HTTPError, ValueError):
            continue
        finally:
            collector.close()
    return (
        {"provider": "unknown", "verified": False}
        if not verified
        else {**verified[0], "candidates": verified}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        result = discover(args.url)
        print(f"Provider: {result['provider']}\nVerified: {str(result['verified']).lower()}")
        if result.get("board_token"):
            print(f"Board token: {result['board_token']}")
    except (ValueError, httpx.HTTPError, OSError) as exc:
        print(f"Provider: unknown\nVerified: false\nReason: {type(exc).__name__}")
        raise SystemExit(1) from None
