"""Outbound-call concurrency.

The limit that gates dialing is **per scheduling batch**: each batch (one schedule action, or
one API call) runs up to ``max_concurrency`` calls at once, and the next fires as one finishes.
That value is stored on the batch's ``scheduled_calls`` rows and enforced at dispatch (see
``OutboundCallService``).

``MAX_CONCURRENT_OUTBOUND_CALLS`` (env) is NOT a separate runtime ceiling — it is only the UI
selector's upper bound AND the default when a batch doesn't specify one (so an API-scheduled
batch with no UI still gets a sane limit). ``resolve_batch_concurrency`` is the ONE place that
turns a requested value into the effective per-batch limit; call it, never re-derive it.
"""

from __future__ import annotations

from typing import Optional

from shared.config import settings


def get_env_outbound_ceiling() -> Optional[int]:
    """The env upper bound (``MAX_CONCURRENT_OUTBOUND_CALLS``) or ``None`` when unset (``<= 0``).
    This is what the UI caps its selector to and defaults it to."""
    cap = settings.MAX_CONCURRENT_OUTBOUND_CALLS
    return cap if isinstance(cap, int) and cap > 0 else None


def resolve_batch_concurrency(requested: Optional[int]) -> Optional[int]:
    """Resolve a batch's effective ``max_concurrency`` — the SINGLE place this is decided, so
    the UI, the file upload, and the API-without-UI all behave the same:

    - a valid ``requested`` (positive int) → clamped to ``[1, env ceiling]`` (or used as-is when
      no env ceiling is set);
    - ``None`` / ``0`` / invalid (empty field, or a programmatic call that omits it) → the env
      ceiling as the DEFAULT;
    - env ceiling also unset → ``None`` (no per-batch limit; dial with no throttle).
    """
    ceiling = get_env_outbound_ceiling()
    try:
        req = int(requested)
    except (TypeError, ValueError):
        req = 0
    if req <= 0:
        return ceiling
    return min(req, ceiling) if ceiling is not None else req
