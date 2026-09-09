"""Factory for the per-direction webhook-failure policy.

Add a direction = a new ``WebhookFailureStrategy`` subclass + a line here; the
runner never branches on the direction string itself.
"""

from __future__ import annotations

from typing import Optional

from core.services.agents.webhook_failure_strategies.base import (
    WebhookFailureStrategy,
)
from core.services.agents.webhook_failure_strategies.inbound import (
    InboundFailureStrategy,
)
from core.services.agents.webhook_failure_strategies.outbound import (
    OutboundFailureStrategy,
)


def get_failure_strategy(direction: Optional[str]) -> WebhookFailureStrategy:
    if direction == "outbound":
        return OutboundFailureStrategy()
    return InboundFailureStrategy()


__all__ = [
    "WebhookFailureStrategy",
    "InboundFailureStrategy",
    "OutboundFailureStrategy",
    "get_failure_strategy",
]
