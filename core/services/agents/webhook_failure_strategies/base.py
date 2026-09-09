"""Per-direction policy for what happens when the call-start webhook fails.

Inbound and outbound differ: an inbound call degrades gracefully (unfilled
variables fall back to defaults, the caller is already connected), while the
intended outbound policy is to abort the call. Expressing this as a strategy
(instead of an ``if direction ==`` in the runner) keeps the deferred outbound
decision in ONE place — the runner never changes when it lands.
"""

from __future__ import annotations


class WebhookFailureStrategy:
    """Base policy: degrade gracefully (no fill, call continues)."""

    # Whether a failure should abort the call. The runner consults this; v1
    # keeps it False for both directions.
    abort: bool = False

    def on_failure(self) -> dict[str, str]:
        """Return the enrichment map to use after a failure (``{}`` = none)."""
        return {}
