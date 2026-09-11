"""Runtime call-termination registry + orchestration.

``terminate_call(...)`` is the ONE provider-agnostic entry point the pipeline
runner calls at teardown to actually drop the phone leg. It picks the provider
strategy, runs it best-effort (never raises), is idempotent per call, and emits a
structured ``call_terminated`` / ``call_ended_error`` log line.

Add a provider = a new ``CallTerminator`` subclass + one line in
``get_call_terminator`` — mirroring ``core/services/call_engines`` and
``core/services/transport/registry.py``.
"""

from typing import Optional

from loguru import logger

from core.services.call_termination.base import CallTerminator
from core.services.call_termination.default import LogOnlyTerminator
from core.services.call_termination.plivo import PlivoTerminator
from core.services.call_termination.sip import SipTerminator
from core.services.call_termination.telnyx import TelnyxTerminator
from core.services.call_termination.twilio import TwilioTerminator
from core.services.call_termination.vonage import VonageTerminator
from core.services.pipeline.call_end_events import (
    EVENT_CALL_ENDED_ERROR,
    EVENT_CALL_TERMINATED,
    log_call_event,
)
from core.utils.telephony import provider_call_id


def get_call_terminator(transport_type: str) -> CallTerminator:
    """Return the runtime terminator for a transport type (unknown → log-only)."""
    if transport_type == "twilio":
        return TwilioTerminator()
    if transport_type == "telnyx":
        return TelnyxTerminator()
    if transport_type == "plivo":
        return PlivoTerminator()
    if transport_type == "vonage":
        return VonageTerminator()
    # SIP trunk calls run on the LiveKit transport (transport_type "livekit");
    # accept "sip" too for safety.
    if transport_type in ("livekit", "sip"):
        return SipTerminator()
    return LogOnlyTerminator(transport_type)


async def terminate_call(
    *,
    transport_type: str,
    call_data: dict,
    org_id: Optional[str],
    reason: Optional[str] = None,
    state: Optional[dict] = None,
) -> bool:
    """Authoritatively hang up the live provider call. Idempotent + best-effort.

    ``state`` is a caller-owned dict (e.g. ``{"done": False}``). When supplied, a
    second invocation for the same call is a no-op, so multiple end paths can call
    this safely. Never raises — a hangup failure must not break pipeline teardown.
    Returns ``True`` on a confirmed hangup ("already ended" counts), else ``False``.
    """
    if state is not None and state.get("done"):
        return True

    call_id = provider_call_id(call_data)
    try:
        ok = await get_call_terminator(transport_type).hangup(call_data, org_id)
    except Exception as e:
        logger.bind(transport_type=transport_type, call_id=call_id).exception(
            "[call-termination] hangup raised for provider={} call_id={}",
            transport_type, call_id,
        )
        log_call_event(
            EVENT_CALL_ENDED_ERROR,
            source="call_terminator",
            reason=reason,
            provider=transport_type,
            call_id=call_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        if state is not None:
            state["done"] = True
        return False

    if state is not None:
        state["done"] = True
    log_call_event(
        EVENT_CALL_TERMINATED,
        source="call_terminator",
        reason=reason,
        provider=transport_type,
        call_id=call_id,
        outcome="success" if ok else "failed",
    )
    return ok


__all__ = ["CallTerminator", "get_call_terminator", "terminate_call"]
