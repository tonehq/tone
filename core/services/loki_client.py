"""Thin, sync Loki HTTP client for reading a single call's logs back.

Only what the per-call log sync needs: a ``query_range`` call with basic auth
and bounded exponential backoff on the transient failures Grafana Cloud throws
(429 with ``Retry-After``, 5xx, timeouts). Deliberately sync (``httpx.Client``)
so it runs inside the Procrastinate worker job and the inline manual endpoint
without dragging an event loop in.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import httpx
from loguru import logger

from shared.config import settings


class LokiError(Exception):
    """Loki query failed in a way the caller should surface (non-retryable, or
    retries exhausted). Carries the HTTP status when there was one."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class LokiLine:
    """One log line from a Loki stream: ns timestamp, text, and stream labels."""

    ts_ns: int
    line: str
    labels: dict


class LokiClient:
    """Reads log lines out of Grafana Cloud Loki via ``/loki/api/v1/query_range``."""

    def __init__(
        self,
        *,
        query_url: Optional[str] = None,
        user: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.query_url = query_url if query_url is not None else settings.LOKI_QUERY_URL
        self.user = user if user is not None else settings.LOKI_QUERY_USER
        self.token = token if token is not None else settings.LOKI_QUERY_TOKEN
        self.timeout = timeout if timeout is not None else settings.LOKI_SYNC_HTTP_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.LOKI_SYNC_MAX_RETRIES

    def query_range(
        self,
        query: str,
        start_ns: int,
        end_ns: int,
        *,
        limit: int,
        direction: str = "forward",
    ) -> List[LokiLine]:
        """Run one LogQL ``query`` over ``[start_ns, end_ns]`` and return its lines.

        Loki's ``query_range`` returns ``data.result[*] = {stream, values:[[ts_ns, line], ...]}``.
        We flatten every stream's values into ``LokiLine``s, carrying that stream's
        labels onto each line. Raises :class:`LokiError` on a non-retryable status
        or once retries are exhausted."""
        params = {
            "query": query,
            "start": str(start_ns),
            "end": str(end_ns),
            "limit": str(limit),
            "direction": direction,
        }
        payload = self._request_with_backoff(params)
        return self._parse(payload)

    # ── internals ──────────────────────────────────────────────────────────

    def _parse(self, payload: dict) -> List[LokiLine]:
        lines: List[LokiLine] = []
        result = ((payload or {}).get("data") or {}).get("result") or []
        for stream in result:
            labels = stream.get("stream") or {}
            for value in stream.get("values") or []:
                # Each value is [ts_ns_str, line]. Skip malformed pairs rather
                # than dropping the whole page.
                try:
                    ts_ns = int(value[0])
                    line = value[1]
                except (IndexError, TypeError, ValueError):
                    logger.debug("[loki] skipping malformed value pair: {}", value)
                    continue
                lines.append(LokiLine(ts_ns=ts_ns, line=line, labels=labels))
        return lines

    def _request_with_backoff(self, params: dict) -> dict:
        """GET the query URL, retrying transient failures with capped exponential
        backoff. Honors ``Retry-After`` on 429. Gives up after ``max_retries``."""
        attempt = 0
        while True:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(self.query_url, params=params, auth=(self.user, self.token))
                status = resp.status_code
                if status == 200:
                    return resp.json()
                if status in (401, 403):
                    # Auth/scope problem — retrying won't help. Surface clearly.
                    raise LokiError(
                        f"Loki auth failed ({status}); token likely lacks logs:read scope",
                        status_code=status,
                    )
                if status == 429 or status >= 500:
                    retry_after = self._retry_after_seconds(resp)
                    self._sleep_or_raise(attempt, status, retry_after)
                    attempt += 1
                    continue
                # Other 4xx (e.g. 400 bad LogQL) — non-retryable.
                raise LokiError(f"Loki query failed ({status}): {resp.text[:500]}", status_code=status)
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                # Transport-level failure — expected/transient, retry within budget.
                if attempt >= self.max_retries:
                    raise LokiError(f"Loki query failed after {attempt} retries: {exc}") from exc
                logger.debug("[loki] transport error, retrying (attempt {}): {}", attempt, exc)
                self._backoff_sleep(attempt)
                attempt += 1

    def _sleep_or_raise(self, attempt: int, status: int, retry_after: Optional[float]) -> None:
        if attempt >= self.max_retries:
            raise LokiError(f"Loki query failed ({status}) after {attempt} retries", status_code=status)
        if retry_after is not None:
            logger.debug("[loki] {} — honoring Retry-After={}s (attempt {})", status, retry_after, attempt)
            time.sleep(retry_after)
        else:
            self._backoff_sleep(attempt)

    @staticmethod
    def _retry_after_seconds(resp: httpx.Response) -> Optional[float]:
        raw = resp.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            # HTTP-date form is uncommon from Loki; fall back to normal backoff.
            return None

    @staticmethod
    def _backoff_sleep(attempt: int) -> None:
        # 0.5, 1, 2, 4, 8 … capped at 30s.
        time.sleep(min(30.0, 0.5 * (2 ** attempt)))
