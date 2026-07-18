"""Shared timing telemetry for tool-call handlers.

Every tool handler in the pipeline (custom webhook, MCP, read_document, built-in
send_sms/google_calendar/end_call) records the same three lifecycle timestamps
onto its ``tool_call_entry`` dict so the ``tool_executions`` row carries a
consistent shape:

* ``llm_requested_at`` — the moment the LLM asked to run this tool. Stamped
  synchronously by :class:`LlmRequestStamper` on handler dispatch. See that
  class's docstring for why this can't be captured from a pipecat observer.
* ``invoked_at``       — the moment the handler body starts running.
* ``completed_at``     — the moment the handler returns (success or error).

Centralised here so the four handler families share one contract and
``ToolExecutionService`` parses the entries uniformly.
"""

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# {tool_call_id -> llm_requested_at datetime}. Populated by ``LlmRequestStamper``
# at handler dispatch and popped by each handler via ``ToolCallTimer.start``.
# Bounded by in-flight tool calls per call.
ToolRequestTsMap = Dict[str, datetime]

ToolHandler = Callable[[Any], Awaitable[Any]]


class ToolCallTimer:
    """Records handler-side timing for a single tool invocation.

    Instantiated at handler entry via :meth:`start`, then :meth:`finish` is
    called on every exit path (success and error). The ``llm_requested_at``
    stamp is looked up up-front from the runner-owned ``tool_request_ts``
    map, keyed by the LLM's ``tool_call_id``.
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
        that don't wire :class:`LlmRequestStamper` yet.
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


class LlmRequestStamper:
    """Stamps ``llm_requested_at`` synchronously on every tool handler dispatch.

    **Why a wrapper, not an observer.**
    Pipecat's ``TaskObserver`` queues frame events into an ``asyncio.Queue``
    that is drained by a background task, so an observer listening for
    ``FunctionCallInProgressFrame`` cannot stamp before the LLM service's
    per-call task calls the handler. The handler's synchronous prefix
    (``ToolCallTimer.start``) then pops from an empty map and
    ``llm_requested_at`` ends up NULL.

    Wrapping ``llm.register_function`` runs the stamp in the SAME asyncio
    task as the handler, before any ``await`` yield — so the pop always
    finds the stamp. There is no race.

    Composes with other ``register_function`` wrappers (e.g. MCP's logging
    wrapper) as long as :meth:`install` is called FIRST — the stamp then
    sits as the outermost wrapper, running before any downstream logic.
    """

    def __init__(self, tool_request_ts: ToolRequestTsMap) -> None:
        self._tool_request_ts = tool_request_ts

    def install(self, llm: Any) -> None:
        """Patch ``llm.register_function`` to wrap every future handler."""
        original_register = llm.register_function
        wrap = self._wrap

        def register_with_stamp(name: str, handler: ToolHandler, *args: Any, **kwargs: Any):
            return original_register(name, wrap(handler), *args, **kwargs)

        llm.register_function = register_with_stamp

    def _wrap(self, handler: ToolHandler) -> ToolHandler:
        """Return a handler that stamps ``tool_request_ts`` then delegates."""
        tool_request_ts = self._tool_request_ts

        async def stamped(params: Any) -> Any:
            tool_call_id = getattr(params, "tool_call_id", None)
            if tool_call_id is not None:
                # setdefault: first-write-wins so a retry / re-emit doesn't
                # overwrite the true LLM-request moment with a later value.
                tool_request_ts.setdefault(tool_call_id, _now_utc())
            return await handler(params)

        return stamped
