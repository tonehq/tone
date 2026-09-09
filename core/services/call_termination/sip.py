"""SIP runtime hangup via LiveKit room deletion.

SIP trunk calls are bridged through a LiveKit room, so the live call id
(``call_data["call_id"]``, transport_type ``livekit``) is the room name. Deleting
the room disconnects every participant — including the SIP/PSTN caller —
regardless of the caller's participant identity (which differs inbound vs
outbound). That is more robust than removing a specific participant by a guessed
identity, and it's the correct end action for any LiveKit-bridged call.
"""

import asyncio
from typing import Optional

from loguru import logger

from core.services.call_engines import get_call_engine
from core.services.call_termination.base import CallTerminator


class SipTerminator(CallTerminator):
    @property
    def provider_name(self) -> str:
        return "sip"

    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        room = (call_data or {}).get("call_id") or ""
        if not room:
            logger.warning("[call-termination] sip hangup skipped — no room (call_id) in call_data")
            return False
        engine = get_call_engine("sip", org_id=org_id)
        # SipCallEngine.end_room runs the LiveKit API via asyncio.run (its own
        # loop), so it MUST be offloaded — calling it inline would fail inside the
        # runner's already-running event loop.
        return await asyncio.to_thread(engine.end_room, room)
