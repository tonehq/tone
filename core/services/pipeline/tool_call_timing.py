"""Shared timing telemetry for tool-call handlers.

Every tool handler in the pipeline (custom webhook, MCP, read_document, built-in
send_sms/google_calendar/end_call) records the same three lifecycle timestamps
onto its ``tool_call_entry`` dict so the ``tool_executions`` row carries a
consistent shape:

* ``llm_requested_at`` — when pipecat pushed the ``FunctionCallInProgressFrame``
  (the LLM decided to call this tool). Captured by the runner's observer and
  looked up here by ``tool_call_id``.
* ``invoked_at``  — the moment the handler body starts running.
* ``completed_at`` — the moment the handler returns (success or error).

Centralised here so the four handler families share one contract and
``ToolExecutionService`` parses the entries uniformly.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# The runner-owned {tool_call_id -> llm_requested_at} map. Populated by the
# observer on the first ``FunctionCallInProgressFrame`` push for each call and
# popped by ``ToolCallTimer.start`` when the handler runs.
ToolRequestTsMap = Dict[str, datetime]


class ToolCallTimer:
    """Records handler-side timing for a single tool invocation.

    Instantiated at handler entry via :meth:`start`, then :meth:`finish` is
    called on every exit path (success and error). The ``llm_requested_at``
    stamp is looked up up-front from the runner-owned
    ``tool_request_ts`` map, keyed by the LLM's ``tool_call_id``.
    """

    __slots__ = ("_llm_requested_at", "_invoked_at")

    def __init__(
        self,
        llm_requested_at: Optional[datetime],
        invoked_at: datetime,
    ) -> None:
        self._llm_requested_at = llm_requested_at
        self._invoked_at = invoked_at

    @classmethod
    def start(
        cls,
        params: Any,
        tool_request_ts: Optional[ToolRequestTsMap],
    ) -> "ToolCallTimer":
        """Stamp ``invoked_at`` NOW and resolve ``llm_requested_at`` for this call.

        The map is popped (not read) so its size stays bounded to in-flight
        calls. Missing entries fall through to None — safe for legacy callers
        that don't wire the observer yet.
        """
        llm_requested_at: Optional[datetime] = None
        if tool_request_ts is not None:
            tool_call_id = getattr(params, "tool_call_id", None)
            if tool_call_id is not None:
                llm_requested_at = tool_request_ts.pop(tool_call_id, None)
        return cls(llm_requested_at=llm_requested_at, invoked_at=_now_utc())

    def initial_fields(self) -> dict:
        """Timestamp fields to merge into the ``tool_call_entry`` at construction."""
        return {
            "llm_requested_at": _iso(self._llm_requested_at),
            "invoked_at": _iso(self._invoked_at),
        }

    def finish(self, entry: dict) -> None:
        """Stamp ``completed_at`` on ``entry``. Call on every exit path."""
        entry["completed_at"] = _iso(_now_utc())


def record_llm_request(
    tool_request_ts: Optional[ToolRequestTsMap],
    tool_call_id: Optional[str],
) -> None:
    """Stamp ``llm_requested_at`` for a tool_call_id as soon as the LLM asks.

    Called by the runner's ``FunctionCallInProgressFrame`` observer. First
    write wins: pipecat pushes each frame through every downstream processor,
    so the observer sees the same frame more than once — we want the earliest
    observation, not the latest. No-op when the map is unwired (older
    callers) or the frame carries no ``tool_call_id``.
    """
    if tool_request_ts is None or not tool_call_id:
        return
    if tool_call_id in tool_request_ts:
        return
    tool_request_ts[tool_call_id] = _now_utc()


def finalize_and_record(
    entry: dict,
    timer: ToolCallTimer,
    tool_call_entries: Optional[list],
) -> None:
    """Stamp ``completed_at`` on ``entry`` and append it to the runner's sink.

    Every handler exit path (success and error) calls this exactly once, so
    the per-call ``tool_executions`` row carries the completion timestamp
    regardless of which code path terminated the call.

    Safe to call with ``tool_call_entries=None`` — the timestamp is still
    stamped so callers that hold the dict directly (e.g. MCP's shared
    ``entry``) still see it.
    """
    timer.finish(entry)
    if tool_call_entries is not None:
        tool_call_entries.append(entry)
