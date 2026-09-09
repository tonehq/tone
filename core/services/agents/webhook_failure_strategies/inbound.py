from __future__ import annotations

from core.services.agents.webhook_failure_strategies.base import (
    WebhookFailureStrategy,
)


class InboundFailureStrategy(WebhookFailureStrategy):
    """Inbound: graceful. A webhook failure/timeout means no enrichment — the
    call continues and webhook variables fall back to their default ``value``."""

    abort = False

    def on_failure(self) -> dict[str, str]:
        return {}
