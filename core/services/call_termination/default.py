"""Fallback terminator for providers without a runtime REST hangup yet.

Covers exotel / plivo / websocket / test. It logs the coverage gap and reports
failure (so the gap is visible) instead of silently pretending the leg dropped.
Enable a provider by adding a real ``CallTerminator`` subclass and registering it
in ``__init__.py`` — no change to the runner or the orchestration.
"""

from typing import Optional

from loguru import logger

from core.services.call_termination.base import CallTerminator


class LogOnlyTerminator(CallTerminator):
    def __init__(self, transport_type: str):
        self._transport_type = transport_type

    @property
    def provider_name(self) -> str:
        return self._transport_type

    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        logger.warning(
            "[call-termination] no runtime hangup implemented for provider={} — "
            "media stream closed but the provider leg may linger",
            self._transport_type,
        )
        return False
