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
# Emitted when the end_call tool handler refuses a tool invocation because
# the mandatory two-step confirmation flow was not completed (no prior
# confirmation ask from the assistant, or no subsequent user reply). Useful
# for alerting on LLM bypass attempts.
EVENT_END_CALL_BLOCKED = "end_call_blocked"

REASON_LLM_END_CALL = "llm_end_call"
REASON_CLIENT_DISCONNECT = "client_disconnect"


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
