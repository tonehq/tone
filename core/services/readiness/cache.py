"""Deep-check result cache with concurrent-request coalescing.

Deep readiness runs spend real money and hit provider rate limits. This cache
serves two related concerns:

- **TTL**: within ``ttl_seconds``, the same key returns the same report without
  hitting providers.
- **Coalescing**: if a second caller asks for the same key while the first is
  still computing, it waits on the first future instead of firing its own
  request. This prevents a UI double-click from doubling provider cost.

In-memory single-worker for v1. Interface is deliberately Redis-swappable —
the service just calls ``get_or_compute(key, compute)``; adding a distributed
backend later means writing a new implementation of this class, not touching
callers.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple
from uuid import UUID

from core.services.readiness.schemas import ReadinessReport


def _norm(value: Any) -> str:
    """Canonicalise a key component so callers that pass a ``UUID`` and callers
    that pass its raw (possibly upper-cased / differently-formatted) string
    build the SAME key.

    Without this, the write path (which passes resolved ``UUID`` objects) and
    the publish-invalidation path (which passes the raw request strings) could
    produce different keys — so ``invalidate`` would silently miss and a stale
    deep report could be served for up to the TTL after a publish. UUID-shaped
    values normalise to their canonical lowercase form; ``None`` maps to a
    stable sentinel; anything else falls back to ``str`` unchanged.
    """
    if value is None:
        return "none"
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return str(value)


class DeepCheckCache:
    """TTL + inflight-coalescing cache keyed by an arbitrary string."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl = ttl_seconds
        self._entries: Dict[str, Tuple[float, ReadinessReport]] = {}
        self._inflight: Dict[str, asyncio.Future[ReadinessReport]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def key(org_id, agent_id, config_id, stamp=None) -> str:
        """Build a cache key. ``config_id`` may be None (means "the resolved
        active config") — its sentinel is kept distinct from any real id so the
        resolved-vs-explicit distinction never collapses two logically distinct
        checks onto one entry.

        ``stamp`` is the agent's dependency fingerprint (see
        ``ReadinessService._compute_stamp``) — it changes whenever ANY input a
        deep check reads changes (config, API keys, OAuth connections, tools,
        KBs, MCP servers, phone). Folding it into the key means a change the
        user makes WITHOUT republishing (e.g. reconnecting an OAuth account or
        adding a key) produces a NEW key, so the stale entry is skipped and a
        fresh check runs — the cache self-invalidates instead of serving a
        5-minute-stale result. ``None`` (no resolvable stamp) uses a sentinel.

        Each id component is canonicalised (see ``_norm``) so a ``UUID`` and its
        raw string form map to the same key — this is what lets the publish
        flow's ``invalidate`` reliably match the entry the deep run wrote."""
        return f"{_norm(org_id)}:{_norm(agent_id)}:{_norm(config_id)}:{stamp or 'nostamp'}"

    async def get_or_compute(
        self,
        key: str,
        compute: Callable[[], Awaitable[ReadinessReport]],
    ) -> ReadinessReport:
        """Return a fresh entry from cache, or await someone else's inflight
        computation, or compute it ourselves and cache the result."""
        future_to_wait: Optional[asyncio.Future[ReadinessReport]] = None
        our_future: Optional[asyncio.Future[ReadinessReport]] = None

        async with self._lock:
            fresh = self._peek_fresh(key)
            if fresh is not None:
                return fresh
            if key in self._inflight:
                future_to_wait = self._inflight[key]
            else:
                our_future = asyncio.get_running_loop().create_future()
                self._inflight[key] = our_future

        if future_to_wait is not None:
            return await future_to_wait

        # We took responsibility — compute, publish, and clean up.
        assert our_future is not None
        try:
            result = await compute()
        except BaseException as exc:
            async with self._lock:
                self._inflight.pop(key, None)
            if not our_future.done():
                our_future.set_exception(exc)
            raise
        else:
            async with self._lock:
                self._entries[key] = (time.monotonic(), result)
                self._inflight.pop(key, None)
            if not our_future.done():
                our_future.set_result(result)
            return result

    def invalidate(self, key: str) -> None:
        """Drop a cached entry. Called by publish flows so the next readiness
        run sees the freshly-published config, not a 5-min-stale snapshot."""
        self._entries.pop(key, None)

    # ── internals ──────────────────────────────────────────────────────────

    def _peek_fresh(self, key: str) -> Optional[ReadinessReport]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, report = entry
        if (time.monotonic() - stored_at) >= self.ttl:
            # Expired — evict lazily.
            self._entries.pop(key, None)
            return None
        return report
