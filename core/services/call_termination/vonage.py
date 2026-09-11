import asyncio
from typing import Optional

from loguru import logger

from core.services.call_engines import get_call_engine
from core.services.call_termination.base import CallTerminator


class VonageTerminator(CallTerminator):
    @property
    def provider_name(self) -> str:
        return "vonage"

    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        call_uuid = (call_data or {}).get("call_id") or ""
        if not call_uuid:
            logger.warning("[call-termination] vonage hangup skipped — no call_id in call_data")
            return False
        engine = get_call_engine("vonage", org_id=org_id)
        return await asyncio.to_thread(engine.end_call, call_uuid)
