"""Unit tests for tool-call timing.

Pins down the race-free contract between :class:`LlmRequestStamper` and
:class:`ToolCallTimer` — specifically that ``llm_requested_at`` is always
populated for a handler that runs through the stamper, even though pipecat's
``TaskObserver`` cannot deliver frame events in-band.

Source:
    core/services/pipeline/tool_call_timing.py

Regression guard: prior to the switch from observer to
``register_function`` wrapper, ``llm_requested_at`` was NULL for most rows
because the observer's stamp ran on a background task that hadn't been
scheduled by the time the handler synchronously popped the map.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import List, Optional

import pytest

from core.services.pipeline.tool_call_timing import (
    LlmRequestStamper,
    ToolCallTimer,
    ToolRequestTsMap,
    finalize_and_record,
)


# ---------------------------------------------------------------------------
# Helpers — a minimal fake pipecat LLM. Only ``register_function`` is used.
# ---------------------------------------------------------------------------


class _FakeLlm:
    """Duck-typed stand-in for ``pipecat.services.LLMService``.

    Only implements ``register_function`` — the surface :class:`LlmRequestStamper`
    patches — plus a ``dispatch`` helper that mimics pipecat's per-call task
    calling the registered handler.
    """

    def __init__(self) -> None:
        self._handlers: dict = {}

    def register_function(self, name: str, handler):
        self._handlers[name] = handler

    async def dispatch(self, name: str, params) -> object:
        return await self._handlers[name](params)


def _params(tool_call_id: Optional[str], name: str = "weather"):
    """Duck-typed ``FunctionCallParams`` — only ``tool_call_id`` is read."""
    return SimpleNamespace(tool_call_id=tool_call_id, function_name=name, arguments={})


# ---------------------------------------------------------------------------
# ToolCallTimer — the read side.
# ---------------------------------------------------------------------------


class TestToolCallTimer:
    def test_start_returns_none_when_map_is_empty(self):
        """Baseline: no stamp → llm_requested_at is None, invoked_at is now."""
        timer = ToolCallTimer.start(_params("call-1"), tool_request_ts={})
        fields = timer.initial_fields()

        assert fields["llm_requested_at"] is None
        assert fields["invoked_at"] is not None

    def test_start_pops_stamped_entry(self):
        """A pre-stamped entry is popped and surfaces as llm_requested_at."""
        request_ts: ToolRequestTsMap = {}
        LlmRequestStamper(request_ts)._wrap(_noop_handler)  # not called yet
        # Simulate a wrapper having stamped the entry.
        from datetime import datetime, timezone
        stamp = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
        request_ts["call-2"] = stamp

        timer = ToolCallTimer.start(_params("call-2"), tool_request_ts=request_ts)
        fields = timer.initial_fields()

        assert fields["llm_requested_at"] == stamp.isoformat()
        # And the map is drained — bounded to in-flight calls.
        assert "call-2" not in request_ts

    def test_start_handles_none_map(self):
        """None map is a no-op — used by legacy callers that don't wire the stamper."""
        timer = ToolCallTimer.start(_params("call-3"), tool_request_ts=None)
        assert timer.initial_fields()["llm_requested_at"] is None

    def test_start_handles_none_tool_call_id(self):
        """A frame without a tool_call_id (very old LLMs) must not KeyError."""
        timer = ToolCallTimer.start(_params(tool_call_id=None), tool_request_ts={})
        assert timer.initial_fields()["llm_requested_at"] is None

    def test_finalize_stamps_completed_at_and_appends(self):
        """finalize_and_record stamps completed_at and appends to the sink."""
        entry: dict = {}
        sink: List[dict] = []
        timer = ToolCallTimer.start(_params("call-4"), tool_request_ts={})
        finalize_and_record(entry, timer, sink)

        assert entry["completed_at"] is not None
        assert sink == [entry]

    def test_finalize_without_sink_still_stamps(self):
        """Handlers that own their entry directly (MCP) pass sink=None."""
        entry: dict = {}
        timer = ToolCallTimer.start(_params("call-5"), tool_request_ts={})
        finalize_and_record(entry, timer, None)

        assert entry["completed_at"] is not None


# ---------------------------------------------------------------------------
# LlmRequestStamper — the write side. THIS is the regression guard.
# ---------------------------------------------------------------------------


async def _noop_handler(_params) -> str:
    return "ok"


class TestLlmRequestStamper:
    def test_stamp_before_handler_body_runs(self):
        """The wrapper stamps the map BEFORE the handler body sees it.

        This is the exact scenario that broke with the observer: the handler
        pops synchronously at entry, and the stamp must already be present.
        """
        request_ts: ToolRequestTsMap = {}
        llm = _FakeLlm()
        LlmRequestStamper(request_ts).install(llm)

        popped: dict = {}

        async def handler(params):
            popped["llm_requested_at"] = request_ts.pop(params.tool_call_id, None)
            return "ok"

        llm.register_function("weather", handler)
        result = asyncio.run(llm.dispatch("weather", _params("call-A")))

        assert result == "ok"
        assert popped["llm_requested_at"] is not None, (
            "regression: handler saw an empty map — stamp did not run in-band"
        )

    def test_stamp_uses_setdefault_semantics(self):
        """A pre-existing entry is not overwritten (first-write-wins)."""
        request_ts: ToolRequestTsMap = {}
        from datetime import datetime, timezone
        pre_stamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        request_ts["call-B"] = pre_stamp

        llm = _FakeLlm()
        LlmRequestStamper(request_ts).install(llm)
        llm.register_function("weather", _noop_handler)

        asyncio.run(llm.dispatch("weather", _params("call-B")))

        assert request_ts["call-B"] == pre_stamp

    def test_stamp_skips_when_tool_call_id_is_none(self):
        """No tool_call_id → nothing to key on → skip cleanly (no KeyError)."""
        request_ts: ToolRequestTsMap = {}
        llm = _FakeLlm()
        LlmRequestStamper(request_ts).install(llm)
        llm.register_function("weather", _noop_handler)

        result = asyncio.run(llm.dispatch("weather", _params(tool_call_id=None)))

        assert result == "ok"
        assert request_ts == {}

    def test_stamp_and_timer_end_to_end(self):
        """The intended two-step: wrapper stamps, then ToolCallTimer.start pops.

        Mirrors what every real tool handler does at its first line.
        """
        request_ts: ToolRequestTsMap = {}
        llm = _FakeLlm()
        LlmRequestStamper(request_ts).install(llm)

        observed: dict = {}

        async def handler(params):
            timer = ToolCallTimer.start(params, request_ts)
            observed.update(timer.initial_fields())
            return "ok"

        llm.register_function("weather", handler)
        asyncio.run(llm.dispatch("weather", _params("call-C")))

        assert observed["llm_requested_at"] is not None
        assert observed["invoked_at"] is not None
        assert observed["llm_requested_at"] <= observed["invoked_at"]

    def test_composes_with_downstream_wrapper(self):
        """MCP-style scenario: a second wrapper installs AFTER the stamper.

        The stamp must still fire first at call time (outermost wrapper wins
        because MCP's ``original_register`` is our ``register_with_stamp``).
        """
        request_ts: ToolRequestTsMap = {}
        llm = _FakeLlm()
        LlmRequestStamper(request_ts).install(llm)

        # Simulate MCP's logging wrapper installed on top.
        original_register = llm.register_function
        call_order: List[str] = []

        def logging_register(name, handler, *args, **kwargs):
            async def logged(params):
                call_order.append("logging_wrapper")
                # By this point the stamp should already have fired.
                assert params.tool_call_id in request_ts, (
                    "regression: stamp did not run before downstream wrapper"
                )
                return await handler(params)

            return original_register(name, logged, *args, **kwargs)

        llm.register_function = logging_register

        async def leaf_handler(params):
            call_order.append("leaf_handler")
            return "ok"

        llm.register_function("weather", leaf_handler)
        asyncio.run(llm.dispatch("weather", _params("call-D")))

        assert call_order == ["logging_wrapper", "leaf_handler"]

    def test_no_yield_between_dispatch_and_handler_body(self):
        """Race guard: no ``await`` yield happens between register and pop.

        This is the specific asyncio-scheduling invariant that made the
        observer-based approach unreliable. Here we assert it by running a
        second task concurrently: if the wrapper had any pre-handler yield,
        the other task could interleave and see an empty map before the
        stamp landed.
        """
        request_ts: ToolRequestTsMap = {}
        llm = _FakeLlm()
        LlmRequestStamper(request_ts).install(llm)

        interleave_saw: dict = {"map_empty_at_pop": None}

        async def handler(params):
            # Snapshot the map BEFORE any await — this is exactly where
            # ToolCallTimer.start pops in real handlers.
            interleave_saw["map_empty_at_pop"] = (
                params.tool_call_id not in request_ts
            )
            return "ok"

        llm.register_function("weather", handler)
        asyncio.run(llm.dispatch("weather", _params("call-E")))

        assert interleave_saw["map_empty_at_pop"] is False, (
            "regression: stamp ran after the handler's synchronous prefix — "
            "the same race the observer version suffered"
        )
