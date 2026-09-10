from __future__ import annotations

from core.services.agents.webhook_failure_strategies.base import (
    WebhookFailureStrategy,
)


class OutboundFailureStrategy(WebhookFailureStrategy):
    """Outbound: the intended policy is to ABORT the call on webhook failure,
    but that flow is deferred (see the feature PRD). v1 behaves gracefully like
    inbound; when the outbound policy is designed, set ``abort = True`` here and
    have the runner honor it — no change to the runner's call site is needed."""

    abort = False

    def on_failure(self) -> dict[str, str]:
        return {}
