"""Shared timing telemetry for tool-call handlers.

Every tool handler in the pipeline (custom webhook, MCP, read_document, built-in
send_sms/google_calendar/end_call) records the same lifecycle timestamps onto
its ``tool_call_entry`` dict so the ``tool_executions`` row carries a
consistent shape:

* ``proposed_at``      — when pipecat pushed ``FunctionCallsStartedFrame``
  (the LLM decided to call this tool as part of a batch). Captured by
  ``ToolCallProposalObserver`` for every LLM proposal, even ones that never
  execute (unregistered tool name, user interrupted mid-batch).
* ``llm_requested_at`` — the moment the LLM asked to run this tool. Stamped
  synchronously by :class:`LlmRequestStamper` on handler dispatch. See that
  class's docstring for why this can't be captured from a pipecat observer.
* ``invoked_at``       — the moment the handler body starts running.
* ``completed_at``     — the moment the handler returns (success or error).

Centralised here so the four handler families share one contract and
``ToolExecutionService`` parses the entries uniformly. The proposals map is
also the source of truth for synthesising rows for tool calls that never made
it to a handler (see :func:`merge_and_synthesize`).
"""

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# {tool_call_id -> llm_requested_at datetime}. Populated by ``LlmRequestStamper``
# at handler dispatch and popped by each handler via ``ToolCallTimer.start``.
# Bounded by in-flight tool calls per call.
ToolRequestTsMap = Dict[str, datetime]

ToolHandler = Callable[[Any], Awaitable[Any]]


# The runner-owned {tool_call_id -> proposal record} map. Populated by
# ``ToolCallProposalObserver`` on ``FunctionCallsStartedFrame`` (with proposal
# metadata) and enriched on ``FunctionCallCancelFrame`` (status flipped to
# ``cancelled``). Consumed at call completion to (a) enrich executed entries
# with ``proposed_at`` and (b) synthesise rows for proposals that never
# executed. Each record has the shape::
#
#     {
#         "tool_call_id": str,
#         "tool_name": str,
#         "arguments": Any,
#         "proposed_at": datetime,
#         "status": "proposed" | "cancelled",
#         "cancel_reason": str | None,
#         "turn_number": int | None,
#         "consumed": bool,   # flipped True once merged into an executed entry
#     }
#
# ``consumed`` is intentionally a flag rather than a dict pop: an executed
# entry still needs the ``proposed_at`` stamp copied in, so we merge and then
# skip the proposal at synthesis time — no reason to lose the record.
ToolProposalMap = Dict[str, Dict[str, Any]]


# Explicit lifecycle status vocabulary. Kept as constants so callers can use
# named symbols instead of string literals scattered through the codebase.
STATUS_PROPOSED = "proposed"
STATUS_CANCELLED = "cancelled"
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"


class ToolCallTimer:
    """Records handler-side timing for a single tool invocation.

    Instantiated at handler entry via :meth:`start`, then :meth:`finish` is
    called on every exit path (success and error). The ``llm_requested_at``
    stamp is looked up up-front from the runner-owned ``tool_request_ts``
    map, keyed by the LLM's ``tool_call_id``. The same ``tool_call_id`` is
    stamped onto the entry via :meth:`initial_fields` so downstream code can
    correlate the executed row back to its LLM proposal.
    """

    __slots__ = ("_llm_requested_at", "_invoked_at", "_tool_call_id")

    def __init__(
        self,
        llm_requested_at: Optional[datetime],
        invoked_at: datetime,
        tool_call_id: Optional[str] = None,
    ) -> None:
        self._llm_requested_at = llm_requested_at
        self._invoked_at = invoked_at
        self._tool_call_id = tool_call_id

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
        tool_call_id = getattr(params, "tool_call_id", None)
        llm_requested_at: Optional[datetime] = None
        if tool_request_ts is not None and tool_call_id is not None:
            llm_requested_at = tool_request_ts.pop(tool_call_id, None)
        return cls(
            llm_requested_at=llm_requested_at,
            invoked_at=_now_utc(),
            tool_call_id=tool_call_id,
        )

    def initial_fields(self) -> dict:
        """Timestamp + correlation fields merged into the entry at construction.

        Every handler splats the return of this into its ``tool_call_entry``
        dict so ``tool_call_id`` propagates uniformly — no per-handler edits
        needed to keep executed rows joinable to their LLM proposals.
        """
        return {
            "tool_call_id": self._tool_call_id,
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


# ----------------------------------------------------------------------------
# Proposal lifecycle helpers
# ----------------------------------------------------------------------------


def record_proposal(
    proposals: Optional[ToolProposalMap],
    *,
    tool_call_id: Optional[str],
    tool_name: Optional[str],
    arguments: Any,
    turn_number: Optional[int] = None,
) -> None:
    """Stamp ``proposed_at`` for a tool_call_id as soon as the LLM emits it.

    Called by ``ToolCallProposalObserver`` on ``FunctionCallsStartedFrame``.
    First write wins: a single frame is re-observed by every downstream
    processor, so subsequent observations of the same tool_call_id are no-ops.
    Safe with an unwired map (older callers).

    ``turn_number`` is snapshotted so proposals that never make it to a
    handler (which is where the executed entries stamp their own turn) still
    show up in the consolidated per-turn view.
    """
    if proposals is None or not tool_call_id:
        return
    if tool_call_id in proposals:
        return
    proposals[tool_call_id] = {
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "proposed_at": _now_utc(),
        "status": STATUS_PROPOSED,
        "cancel_reason": None,
        "turn_number": turn_number,
        "consumed": False,
    }


def record_cancel(
    proposals: Optional[ToolProposalMap],
    *,
    tool_call_id: Optional[str],
    reason: Optional[str] = None,
) -> None:
    """Flip a proposal to ``cancelled`` when pipecat cancels the tool call.

    Idempotent: the cancel frame can be pushed more than once. Only proposals
    that never reached a completed handler transition to ``cancelled`` — if
    the handler already ran, the entry keeps its ``success``/``error`` status
    (the merge step skips consumed proposals).
    """
    if proposals is None or not tool_call_id:
        return
    proposal = proposals.get(tool_call_id)
    if proposal is None:
        return
    if proposal["status"] == STATUS_PROPOSED:
        proposal["status"] = STATUS_CANCELLED
    if reason and proposal.get("cancel_reason") is None:
        proposal["cancel_reason"] = reason


def merge_and_synthesize(
    executed_entries: Optional[List[dict]],
    proposals: Optional[ToolProposalMap],
) -> List[dict]:
    """Combine executed entries + LLM proposals into one call-completion list.

    Runs at call completion so the resulting list carries a row for **every**
    tool call the LLM proposed:

    * Each executed entry gets its ``proposed_at`` filled in from the matching
      proposal (looked up by ``tool_call_id``), then is emitted as-is.
    * Each unconsumed proposal (never dispatched by the pipeline) is
      synthesised into an entry with ``status=proposed`` or
      ``status=cancelled`` and just the proposal-side fields set.

    Order preserved: executed entries stay in their original invocation order
    (they already sort by ``started_at`` downstream) followed by unexecuted
    proposals in the order pipecat emitted them (dict insertion order).

    Safe with either side missing:
      * proposals=None → executed entries returned unchanged.
      * executed_entries=None → only synthesised proposal rows.
    """
    entries: List[dict] = []

    if executed_entries:
        for entry in executed_entries:
            _merge_proposal_into_entry(entry, proposals)
            entries.append(entry)

    entries.extend(_synthesize_unexecuted_proposals(proposals))
    return entries


def _merge_proposal_into_entry(
    entry: dict,
    proposals: Optional[ToolProposalMap],
) -> None:
    """Copy ``proposed_at`` from the proposal record into an executed entry.

    Marks the proposal ``consumed`` so it isn't also emitted as a synthesised
    row. First-wins on ``proposed_at`` — if the handler already carried one
    (unlikely), we don't overwrite it.
    """
    if proposals is None:
        return
    tool_call_id = entry.get("tool_call_id")
    if not tool_call_id:
        return
    proposal = proposals.get(tool_call_id)
    if proposal is None:
        return
    if not entry.get("proposed_at"):
        entry["proposed_at"] = _iso(proposal["proposed_at"])
    proposal["consumed"] = True


def _synthesize_unexecuted_proposals(
    proposals: Optional[ToolProposalMap],
) -> List[dict]:
    """Emit one entry per proposal that never became an executed entry.

    ``status`` follows the tracked lifecycle (``proposed`` or ``cancelled``).
    Only the proposal-side fields are populated — the execution-side columns
    (invoked_at, completed_at, result, duration_ms) stay unset so downstream
    consumers can tell the row apart from an executed one.
    """
    if not proposals:
        return []

    synthesised: List[dict] = []
    for proposal in proposals.values():
        if proposal.get("consumed"):
            continue
        entry = {
            "tool": proposal.get("tool_name") or "unknown",
            "tool_call_id": proposal.get("tool_call_id"),
            "arguments": proposal.get("arguments"),
            "status": proposal.get("status") or STATUS_PROPOSED,
            "proposed_at": _iso(proposal.get("proposed_at")),
        }
        turn_number = proposal.get("turn_number")
        if turn_number is not None:
            entry["turn"] = turn_number
        cancel_reason = proposal.get("cancel_reason")
        if cancel_reason:
            entry["error"] = cancel_reason
        synthesised.append(entry)
    return synthesised
