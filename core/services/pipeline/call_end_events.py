"""Structured event logging for call end-of-life.

Central home for:
  * The event names (``event=call_ended`` / ``event=call_ended_error``) and
    the reason vocabulary (``llm_end_call`` / ``client_disconnect``) that
    flow both into ``Call.metadata_.ended_reason`` and into the log lines
    Grafana/Loki alert on.
  * ``log_call_event``: a single formatter every termination site calls so
    the emitted line is a stable ``event=... key=value ...`` shape that
    ``| logfmt`` in LogQL can parse without regexes.

Every emitted line inherits the per-call ``trace_id`` from ``core.logging``,
so Grafana can filter/aggregate by call without us having to repeat call_id
in each field list.
"""

from typing import Any

from loguru import logger

EVENT_CALL_ENDED = "call_ended"
EVENT_CALL_ENDED_ERROR = "call_ended_error"
# Emitted by the provider-agnostic terminator (core/services/call_termination)
# after it attempts the authoritative REST hangup at pipeline teardown — records
# the provider, resolved hangup id, and outcome (success/failed).
EVENT_CALL_TERMINATED = "call_terminated"

REASON_LLM_END_CALL = "llm_end_call"
REASON_CLIENT_DISCONNECT = "client_disconnect"
# Stamped by the runner's InactivityMonitor when a call goes silent for longer
# than CALL_INACTIVITY_TIMEOUT_SECS — the model-independent backstop that keeps
# a dead line from hanging open forever (see core/services/pipeline/inactivity_monitor.py).
REASON_INACTIVITY_TIMEOUT = "inactivity_timeout"
# Stamped by the runner's MaxDurationGuard when a call exceeds MAX_CALL_DURATION_SECS
# — the hard ceiling backstop for a runaway call that never goes silent.
REASON_MAX_DURATION = "max_call_duration"
# Stamped when the assistant spoke a clear farewell but never fired end_call —
# a model-independent backstop (see core/services/pipeline/farewell_detection.py)
# so a dropped tool call after "goodbye" still ends the call promptly.
REASON_SPOKEN_FAREWELL = "spoken_farewell"


def _fmt_value(value: Any) -> str:
    """Render a value as a logfmt-safe token.

    Quotes anything that contains whitespace, ``=`` or ``"`` so LogQL's
    ``logfmt`` parser reads it as a single field.
    """
    if value is None:
        return "none"
    s = str(value)
    if any(c in s for c in ' \t\n"=,'):
        s = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'
    return s


def log_call_event(event: str, **fields: Any) -> None:
    """Emit one structured log line in ``event=X key=value`` (logfmt) form.

    Example line as it lands in Grafana::

        ... | INFO | ... | event=call_ended reason=llm_end_call source=llm_tool detail="user said goodbye"

    Query with LogQL::

        {app="tone"} |= "event=call_ended" | logfmt | reason="client_disconnect"
    """
    parts = [f"event={event}"]
    for key, value in fields.items():
        parts.append(f"{key}={_fmt_value(value)}")
    logger.info(" ".join(parts))
