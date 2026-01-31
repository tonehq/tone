"""Service to resolve the bot (agent) for incoming telephony calls by phone number."""

import os
from typing import Optional, Tuple, Any, Dict

import aiohttp
from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_phone_numbers import AgentPhoneNumbers
from core.services.base import BaseService


class BotRunnerService(BaseService):
    """Resolve the bot (agent) for incoming telephony calls by phone number."""

    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number for lookup (strip, optional E.164)."""
        if not phone_number:
            return ""
        return phone_number.strip()

    def get_bot_for_phone_number(self, phone_number: str) -> Optional[Agent]:
        """Find the agent (bot) associated with the given phone number (the number the call came to).

        Args:
            phone_number: The 'To' number (our number that received the call).

        Returns:
            The Agent for that phone number, or None if not found.
        """
        normalized = self._normalize_phone_number(phone_number)
        if not normalized:
            return None
        agent_phone = (
            self.db.query(AgentPhoneNumbers)
            .filter(AgentPhoneNumbers.phone_number == normalized)
            .first()
        )
        if not agent_phone:
            return None
        agent = self.db.query(Agent).filter(Agent.id == agent_phone.agent_id).first()
        return agent

    async def _fetch_twilio_to_number(self, call_sid: str) -> Optional[str]:
        """Fetch the 'to' number for a Twilio call from Twilio REST API."""
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            logger.warning("Missing Twilio credentials, cannot resolve to_number")
            return None
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"
        try:
            auth = aiohttp.BasicAuth(account_sid, auth_token)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth) as response:
                    if response.status != 200:
                        return None
                    data = await response.json()
                    return data.get("to")
        except Exception as e:
            logger.error("Error fetching Twilio call info: %s", e)
            return None

    async def get_to_number_from_call_data_async(
        self, transport_type: str, call_data: Dict[str, Any]
    ) -> Optional[str]:
        """Get the 'to' phone number from parsed call_data (async; handles Twilio API)."""
        if transport_type == "twilio":
            call_sid = call_data.get("call_id")
            if not call_sid:
                return None
            return await self._fetch_twilio_to_number(call_sid)
        return call_data.get("to") or None

    async def get_bot_for_incoming_call(
        self, websocket: Any
    ) -> Tuple[Optional[Agent], str, Dict[str, Any]]:
        """Parse the WebSocket (first messages from /ws), determine the 'to' number, and return the bot (agent) for that number.

        Consumes the first telephony messages from the websocket (same as parse_telephony_websocket).
        Caller should pass the same websocket to the transport so subsequent messages are read by the transport.

        Args:
            websocket: The FastAPI WebSocket from /ws.

        Returns:
            Tuple of (agent or None, transport_type, call_data).
            If no agent is found for the phone number, agent is None.
        """
        from pipecatfork.src.pipecat.runner.utils import parse_telephony_websocket

        transport_type, call_data = await parse_telephony_websocket(websocket)
        print("transport_type ===========", transport_type)
        print("call_data ===========", call_data)
        to_number = await self.get_to_number_from_call_data_async(transport_type, call_data)
        if not to_number:
            logger.warning("Could not determine 'to' phone number from call data")
            return None, transport_type, call_data
        agent = self.get_bot_for_phone_number(to_number)
        if agent:
            logger.info(
                "Resolved bot for to_number=%s -> agent_id=%s name=%s",
                to_number,
                agent.id,
                agent.name,
            )
        else:
            logger.warning("No agent found for phone number: %s", to_number)
        return agent, transport_type, call_data
