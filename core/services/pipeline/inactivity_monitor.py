"""Call-end safety watchdogs.

Two model-independent backstops that guarantee a call cannot run forever. Both
are SAFETY NETS, not the primary end path — the LLM's ``end_call`` tool is still
how calls normally end. Both read no words and infer no intent (that heuristic
path was tried and removed — see the builder's ``CallEndDetectorProcessor``
note), so neither can end a call mid-sentence or mis-read a confirmation.

* :class:`InactivityMonitor` — ends a call after a stretch of complete silence
  (no user turn and no assistant turn), for a dead line (caller walked away, or
  the model spoke a farewell but never fired ``end_call``). ON by default.
* :class:`MaxDurationGuard` — a hard cap on total call length, for a runaway
  call that never goes silent (a stuck loop, or a machine on the line talking
  forever). OFF by default — a fixed ceiling that force-ends even an active
  call, so it is opt-in per environment.

Both share the :class:`_CallEndWatchdog` lifecycle (opt-in, single-shot asyncio
task, cancel-clean ``stop``); they differ only in *what they wait for* (:meth:`_run`).
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional

from loguru import logger

# Default when the env knob (``CALL_INACTIVITY_TIMEOUT_SECS``) is left unset (0).
# Chosen well above natural caller pauses: real callers routinely go quiet for
# 15-20s mid-call — in the end-call incident log the caller paused 18s and was
# still engaged — so a short backstop would cut an engaged caller off. 45s is
# unambiguously a dead line.
DEFAULT_INACTIVITY_TIMEOUT_SECS = 45


def resolve_inactivity_timeout(raw: Optional[int]) -> Optional[int]:
    """Resolve the effective inactivity timeout (seconds) from the raw env value.

    - ``> 0`` → that many seconds.
    - ``0`` / ``None`` (env unset) → :data:`DEFAULT_INACTIVITY_TIMEOUT_SECS` (backstop ON).
    - ``< 0`` → ``None`` (explicitly DISABLED).
    """
    if raw is None or raw == 0:
        return DEFAULT_INACTIVITY_TIMEOUT_SECS
    if raw < 0:
        return None
    return raw


def resolve_max_call_duration(raw: Optional[int]) -> Optional[int]:
    """Resolve the effective max call duration (seconds) from the raw env value.

    - ``> 0`` → that many seconds (a hard cap; force-ends even an active call).
    - ``0`` / ``None`` / ``< 0`` → ``None`` (DISABLED).

    Unlike the inactivity backstop this defaults OFF: it can cut off a live,
    talking call, so it must be opted into per environment (set a positive
    number of seconds, e.g. 1800 for a 30-minute ceiling).
    """
    if raw is None or raw <= 0:
        return None
    return raw


class _CallEndWatchdog:
    """Shared lifecycle for the call-end safety watchdogs.

    An opt-in, single-shot asyncio task that awaits some condition (defined by the
    subclass's :meth:`_run`) and then ends the call once via ``on_timeout``.
    Subclasses set ``threshold_secs`` (seconds; ``None``/``<= 0`` → disabled).
    """

    def __init__(
        self,
        threshold_secs: Optional[float],
        on_timeout: Callable[[], Awaitable[None]],
    ):
        self._threshold = threshold_secs
        self._on_timeout = on_timeout
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    @property
    def enabled(self) -> bool:
        return bool(self._threshold and self._threshold > 0)

    def start(self) -> None:
        """Arm the watchdog. No-op when disabled or already started/stopped."""
        if self.enabled and self._task is None and not self._stopped:
            self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        """Cancel the watchdog and await its task. Idempotent; safe in teardown."""
        self._stopped = True
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:  # pragma: no cover - overridden by subclasses
        raise NotImplementedError


class InactivityMonitor(_CallEndWatchdog):
    """End the call after ``timeout_secs`` of no turn activity.

    Wiring (from the runner)::

        monitor = InactivityMonitor(timeout_secs, on_timeout=_end_call)
        # on each turn boundary event:
        monitor.turn_started(); monitor.turn_ended()
        monitor.start()          # once the session has begun
        await monitor.stop()     # in teardown

    ``on_timeout`` is awaited at most once. A turn that is *in progress* pauses
    the countdown (a long assistant turn never trips the timer); the clock only
    runs during the gap between one turn ending and the next starting.
    """

    def __init__(
        self,
        timeout_secs: Optional[float],
        on_timeout: Callable[[], Awaitable[None]],
    ):
        super().__init__(timeout_secs, on_timeout)
        self._wake = asyncio.Event()
        self._active = False          # a turn is currently in progress

    def turn_started(self) -> None:
        """A turn began — pause the countdown until it ends."""
        self._active = True
        self._wake.set()

    def turn_ended(self) -> None:
        """A turn ended — (re)start the silence countdown from now."""
        self._active = False
        self._wake.set()

    async def _run(self) -> None:
        try:
            while not self._stopped:
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=self._threshold)
                    # Touched (a turn boundary or stop) → restart the countdown.
                    continue
                except asyncio.TimeoutError:
                    # A turn is mid-flight (or we're stopping) → keep waiting.
                    if self._active or self._stopped:
                        continue
                    await self._on_timeout()
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[inactivity-monitor] watchdog loop failed")


class MaxDurationGuard(_CallEndWatchdog):
    """End the call once it has run for ``max_secs``, regardless of activity.

    A one-shot fixed deadline from :meth:`start` — it does NOT reset on turns
    (that's what makes it a *maximum length*, not an idle timer). Wired like the
    inactivity monitor: ``start()`` once the session begins, ``await stop()`` in
    teardown. ``on_timeout`` is awaited at most once.
    """

    async def _run(self) -> None:
        try:
            await asyncio.sleep(self._threshold)
            if not self._stopped:
                await self._on_timeout()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[max-duration-guard] deadline handler failed")
