"""Telnyx runtime hangup via the Call-Control API.

Uses ``POST /v2/calls/{call_control_id}/actions/hangup`` — the SAME endpoint the
Pipecat serializer's ``auto_hang_up`` uses, keyed off the ``call_control_id`` in
the live ``call_data``. This is deliberately NOT ``TelnyxCallEngine.end_call``,
which targets the TeXML API with a TeXML call SID (an origination-time id that
does not match the ``call_control_id`` an answered media call carries).
"""

from typing import Optional

import aiohttp
from loguru import logger

from core.services.call_termination.base import CallTerminator
from core.services.transport.telephony_credentials import get_telnyx_api_key

# Telnyx error code for "Call has already ended" — treat as a successful hangup.
# https://developers.telnyx.com/api/errors/90018
_ALREADY_ENDED_CODE = "90018"


class TelnyxTerminator(CallTerminator):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        call_data = call_data or {}
        call_control_id = call_data.get("call_control_id") or call_data.get("call_id") or ""
        if not call_control_id:
            logger.warning("[call-termination] telnyx hangup skipped — no call_control_id in call_data")
            return False
        api_key = get_telnyx_api_key(org_id=org_id)
        if not api_key:
            logger.warning("[call-termination] telnyx hangup skipped — no api_key for org_id={}", org_id)
            return False

        endpoint = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/hangup"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers) as response:
                if response.status == 200:
                    logger.info("[call-termination] telnyx call hung up cc_id={}", call_control_id)
                    return True
                if response.status == 422:
                    try:
                        data = await response.json()
                        already_ended = any(
                            err.get("code") == _ALREADY_ENDED_CODE
                            for err in data.get("errors", [])
                        )
                    except Exception:
                        # Parse fallback — treat as a non-already-ended 422 below.
                        logger.debug("[call-termination] telnyx 422 body parse failed cc_id={}", call_control_id)
                        already_ended = False
                    if already_ended:
                        logger.debug("[call-termination] telnyx call already ended cc_id={}", call_control_id)
                        return True
                error_text = await response.text()
                logger.error(
                    "[call-termination] telnyx hangup failed cc_id={} status={} body={}",
                    call_control_id, response.status, error_text,
                )
                return False
