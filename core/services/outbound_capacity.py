"""Outbound concurrent-call capacity — the single home for "how many outbound calls may
be dispatched simultaneously".

This is intentionally a **permissive stub** for now: it returns a high, effectively
non-limiting number so current behaviour is unchanged. It exists so every outbound path
asks the SAME function before dispatching — when real throttling is needed (e.g. deriving
headroom from :class:`~core.services.pod_picker.PodPicker` pod metrics, a Twilio
concurrency ceiling, or a per-org ``settings`` cap), the logic lands here and every caller
gets it for free. Do NOT re-implement capacity checks at call sites — call this.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

# A permissive ceiling — large enough to never gate a batch today (outbound batches are
# effectively unbounded). When real capacity logic is added it replaces this constant.
_DEFAULT_OUTBOUND_CAPACITY = 1_000_000


def get_outbound_call_capacity(org_id: Optional[UUID] = None) -> int:
    """Return how many outbound calls may be dispatched concurrently for ``org_id``.

    STUB: returns a permissive constant (no real throttling yet). Callers should invoke
    this before dispatching and dispatch at most the returned number, deferring any
    remainder. ``org_id`` is accepted now so a future per-org cap needs no signature change.
    """
    return _DEFAULT_OUTBOUND_CAPACITY
