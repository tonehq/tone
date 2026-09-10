"""Unit tests for the call inactivity backstop.

Source: core/services/pipeline/inactivity_monitor.py. Timing-based but with
generous margins (short timeout, longer sleeps) so the watchdog's fire / pause /
reset / disable / stop behaviours are exercised without flakiness.
"""

import asyncio

from core.services.pipeline.inactivity_monitor import (
    DEFAULT_INACTIVITY_TIMEOUT_SECS,
    InactivityMonitor,
    MaxDurationGuard,
    resolve_inactivity_timeout,
    resolve_max_call_duration,
)


def test_resolve_defaults_when_unset():
    assert resolve_inactivity_timeout(0) == DEFAULT_INACTIVITY_TIMEOUT_SECS
    assert resolve_inactivity_timeout(None) == DEFAULT_INACTIVITY_TIMEOUT_SECS


def test_resolve_positive_passthrough():
    assert resolve_inactivity_timeout(20) == 20


def test_resolve_negative_disables():
    assert resolve_inactivity_timeout(-1) is None


def _fired_flag():
    state = {"fired": False}

    async def _on_timeout():
        state["fired"] = True

    return state, _on_timeout


def test_fires_after_idle():
    async def _go():
        state, on_timeout = _fired_flag()
        monitor = InactivityMonitor(0.05, on_timeout=on_timeout)
        monitor.start()
        await asyncio.sleep(0.2)
        await monitor.stop()
        return state

    state = asyncio.run(_go())
    assert state["fired"] is True


def test_does_not_fire_while_turn_active():
    async def _go():
        state, on_timeout = _fired_flag()
        monitor = InactivityMonitor(0.05, on_timeout=on_timeout)
        monitor.turn_started()  # a turn is in progress → countdown paused
        monitor.start()
        await asyncio.sleep(0.2)
        active_fired = state["fired"]
        monitor.turn_ended()    # turn ends → countdown runs
        await asyncio.sleep(0.2)
        after_end_fired = state["fired"]
        await monitor.stop()
        return active_fired, after_end_fired

    active_fired, after_end_fired = asyncio.run(_go())
    assert active_fired is False, "must not fire while a turn is active"
    assert after_end_fired is True, "must fire once the turn ends and silence follows"


def test_touch_resets_countdown():
    async def _go():
        state, on_timeout = _fired_flag()
        monitor = InactivityMonitor(0.1, on_timeout=on_timeout)
        monitor.start()
        # Keep touching under the timeout — should never fire.
        for _ in range(4):
            await asyncio.sleep(0.04)
            monitor.turn_ended()
        mid_fired = state["fired"]
        # Now go quiet past the timeout — should fire.
        await asyncio.sleep(0.25)
        await monitor.stop()
        return mid_fired, state["fired"]

    mid_fired, end_fired = asyncio.run(_go())
    assert mid_fired is False
    assert end_fired is True


def test_disabled_never_fires():
    async def _go():
        state, on_timeout = _fired_flag()
        monitor = InactivityMonitor(resolve_inactivity_timeout(-1), on_timeout=on_timeout)
        assert monitor.enabled is False
        monitor.start()
        await asyncio.sleep(0.15)
        await monitor.stop()
        return state

    state = asyncio.run(_go())
    assert state["fired"] is False


def test_stop_before_timeout_is_clean():
    async def _go():
        state, on_timeout = _fired_flag()
        monitor = InactivityMonitor(0.2, on_timeout=on_timeout)
        monitor.start()
        await asyncio.sleep(0.02)
        await monitor.stop()
        await asyncio.sleep(0.3)  # well past the timeout — must stay silent
        return state

    state = asyncio.run(_go())
    assert state["fired"] is False


# ── MaxDurationGuard ──────────────────────────────────────────────────────────


def test_resolve_max_duration_off_by_default():
    assert resolve_max_call_duration(0) is None
    assert resolve_max_call_duration(None) is None
    assert resolve_max_call_duration(-5) is None


def test_resolve_max_duration_positive_passthrough():
    assert resolve_max_call_duration(1800) == 1800


def test_max_duration_fires_regardless_of_activity():
    async def _go():
        state, on_timeout = _fired_flag()
        guard = MaxDurationGuard(0.1, on_timeout=on_timeout)
        guard.start()
        # Keep "talking" the whole time — the cap must fire anyway (it never resets).
        for _ in range(4):
            await asyncio.sleep(0.04)
        await guard.stop()
        return state

    state = asyncio.run(_go())
    assert state["fired"] is True


def test_max_duration_disabled_never_fires():
    async def _go():
        state, on_timeout = _fired_flag()
        guard = MaxDurationGuard(resolve_max_call_duration(0), on_timeout=on_timeout)
        assert guard.enabled is False
        guard.start()
        await asyncio.sleep(0.15)
        await guard.stop()
        return state

    state = asyncio.run(_go())
    assert state["fired"] is False


def test_max_duration_stop_before_deadline_is_clean():
    async def _go():
        state, on_timeout = _fired_flag()
        guard = MaxDurationGuard(0.2, on_timeout=on_timeout)
        guard.start()
        await asyncio.sleep(0.02)
        await guard.stop()
        await asyncio.sleep(0.3)  # past the deadline — must stay silent
        return state

    state = asyncio.run(_go())
    assert state["fired"] is False
