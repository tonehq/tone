"""Twilio runtime hangup.

Reuses the origination engine's ``end_call`` — Twilio's REST hangup keys off the
Call SID, which is exactly the ``call_id`` in the live ``call_data``, so there is
no id mismatch and nothing to re-implement.
"""

import asyncio
from typing import Optional

from loguru import logger

from core.services.call_engines import get_call_engine
from core.services.call_termination.base import CallTerminator


class TwilioTerminator(CallTerminator):
    @property
    def provider_name(self) -> str:
        return "twilio"

    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        call_sid = (call_data or {}).get("call_id") or ""
        if not call_sid:
            logger.warning("[call-termination] twilio hangup skipped — no call_id in call_data")
            return False
        engine = get_call_engine("twilio", org_id=org_id)
        # TwilioCallEngine.end_call is synchronous (Twilio SDK). Offload it so a
        # blocking REST call never stalls the event loop during async teardown.
        return await asyncio.to_thread(engine.end_call, call_sid)
