"""Token-bucket rate limiter for Deep readiness checks.

Coarse — one bucket per ``(org, agent)`` at ``max_per_window`` events per
``window_seconds``. Purely defensive: cache coalescing already prevents
duplicate concurrent runs; this stops a user hammering "Test agent" from
spending cents-per-click on real provider calls after the cache expires.

Single-worker in-memory. Same swap story as the cache — for multi-worker,
back this with Redis (``INCR`` + ``EXPIRE``).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    def __init__(self, max_per_window: int = 1, window_seconds: int = 60) -> None:
        self.max_per_window = max_per_window
        self.window = window_seconds
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    @staticmethod
    def key(org_id, agent_id) -> str:
        return f"{org_id}:{agent_id}"

    async def try_acquire(self, key: str) -> bool:
        """Return True and record the event if under the limit; False otherwise.

        The caller is responsible for turning False into an HTTP 429; we don't
        raise from here because different callers want different responses (a
        gate-publish call may want to hard-fail; a UI probe may want to fall
        back to the cache).
        """
        now = time.monotonic()
        cutoff = now - self.window
        async with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= self.max_per_window:
                return False
            events.append(now)
            return True
