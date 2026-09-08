"""Telnyx runtime hangup via the TeXML API.

This repo originates/answers Telnyx calls over TeXML (Twilio-compatible), so the
live call id is a TeXML CallSid (e.g. "v3:..."). The correct hangup is the TeXML
API (``POST /v2/texml/.../Calls/{sid}`` with ``Status=completed``) — exactly what
``TelnyxCallEngine.end_call`` does. It is deliberately NOT the Call-Control API
(``/v2/calls/{id}/actions/hangup``), which rejects a TeXML SID with a 422
"Invalid Call Control ID" (code 90015).
"""

import asyncio
from typing import Optional

from loguru import logger

from core.services.call_engines import get_call_engine
from core.services.call_termination.base import CallTerminator


class TelnyxTerminator(CallTerminator):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        call_id = (call_data or {}).get("call_id") or ""
        if not call_id:
            logger.warning("[call-termination] telnyx hangup skipped — no call_id in call_data")
            return False
        engine = get_call_engine("telnyx", org_id=org_id)
        # TelnyxCallEngine.end_call is synchronous (requests). Offload it so the
        # blocking REST call never stalls the event loop during async teardown.
        return await asyncio.to_thread(engine.end_call, call_id)
