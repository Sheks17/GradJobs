import random
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from services.api.app.core.config import get_settings
from shared.schemas import NormalizedJob


class Collector(ABC):
    source_type: str
    endpoint: str
    capabilities = {
        "list_jobs": True,
        "fetch_detail": False,
        "pagination": False,
        "source_discovery": True,
        "salary": False,
        "posted_date": False,
        "remote_metadata": True,
        "closing_date": False,
    }

    def __init__(
        self,
        board: str,
        company: str,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        config: dict | None = None,
    ):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", board):
            raise ValueError("Board must be a provider identifier, not a URL")
        self.board, self.company, self.sleep = board, company, sleep
        self.config = config or {}
        self.request_count = self.request_latency_ms = 0
        self.failed_requests = self.rate_limit_responses = 0
        self.snapshot_complete = True
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(get_settings().collector_timeout_seconds, connect=10),
            follow_redirects=False,
            headers={
                "User-Agent": get_settings().collector_user_agent,
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def get_json(
        self, params: dict | None = None, *, url: str | None = None, headers: dict | None = None
    ) -> Any:
        return self.request_json("GET", params=params, url=url, headers=headers)

    def request_json(self, method, *, params=None, url=None, headers=None, json=None) -> Any:
        for attempt in range(4):
            self.sleep(get_settings().collector_request_interval)
            started = time.monotonic()
            self.request_count += 1
            try:
                response = self.client.request(
                    method,
                    url or self.endpoint.format(board=self.board),
                    params=params,
                    headers=headers,
                    json=json,
                )
                self.request_latency_ms += int((time.monotonic() - started) * 1000)
                self.rate_limit_responses += response.status_code == 429
                self.failed_requests += response.status_code >= 400
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < 3:
                        retry = response.headers.get("Retry-After", "")
                        try:
                            delay = max(0, float(retry))
                        except ValueError:
                            try:
                                date = parsedate_to_datetime(retry)
                                delay = max(0, (date - datetime.now(UTC)).total_seconds())
                            except (TypeError, ValueError):
                                delay = 2**attempt
                        if delay > 120:
                            response.raise_for_status()
                        self.sleep(delay + random.uniform(0, 0.3))
                        continue
                response.raise_for_status()
                return response.json()
            except httpx.TransportError:
                self.request_latency_ms += int((time.monotonic() - started) * 1000)
                self.failed_requests += 1
                if attempt == 3:
                    raise
                self.sleep(2**attempt)
        raise RuntimeError("Retry budget exhausted")

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Return a complete snapshot or raise; never pass partial fetches as success."""

    @abstractmethod
    def normalize(self, raw: dict) -> NormalizedJob | None:
        """None means intentionally excluded (e.g. an unlisted posting)."""
