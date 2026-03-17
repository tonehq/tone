"""Service to resolve the bot (agent) for incoming telephony calls by phone number."""

from typing import Optional, Tuple, Any, Dict

import aiohttp
from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_channel import AgentChannel
from core.models.channel_phone_numbers import ChannelPhoneNumbers
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
        print("normalized in bot_runner_service.py file ===========", normalized)
        if not normalized:
            return None
        channel_phone = (
            self.db.query(ChannelPhoneNumbers)
            .filter(ChannelPhoneNumbers.phone_number == normalized)
            .first()
        )
        

        if not channel_phone:
            return None

        # Prefer direct agent_id lookup
        try:
            if channel_phone.agent_id:
                return self.db.query(Agent).filter(Agent.id == channel_phone.agent_id).first()
        except Exception:
            self.db.rollback()

        # Fallback to channel-based lookup for legacy records without agent_id
        if channel_phone.channel_id:
            agent = (
                self.db.query(Agent)
                .join(AgentChannel, AgentChannel.agent_id == Agent.id)
                .filter(AgentChannel.channel_id == channel_phone.channel_id)
                .first()
            )
            return agent

        return None

    def _get_twilio_credentials(self) -> dict:
        """Fetch Twilio account_sid and auth_token from the DB (api_keys table)."""
        from core.models.service_provider import ServiceProvider
        from core.models.api_key import ApiKey
        from core.utils.encryption import decrypt

        provider = self.db.query(ServiceProvider).filter(ServiceProvider.name == "twilio").first()
        print("provider_idd", provider.id)
        if not provider:
            logger.warning("Twilio service provider not found in DB")
            return {}

        api_keys = (
            self.db.query(ApiKey)
            .filter(ApiKey.service_provider_id == provider.id)
            .all()
        )

        print("api_keyss", api_keys)

        creds = {}
        for ak in api_keys:
            additional = ak.additional_credentials or {}
            key_type = additional.get("key_type")
            print("key_typee", key_type)
            if key_type == "account_sid":
                creds["account_sid"] = decrypt(ak.api_key_encrypted)
            if key_type == "auth_token":
                creds["auth_token"] = decrypt(ak.api_key_encrypted)

        print("credssss", creds)
        return creds

    async def _fetch_twilio_to_number(self, call_sid: str) -> Optional[str]:
        """Fetch the 'to' number for a Twilio call from Twilio REST API."""
        twilio_creds = self._get_twilio_credentials()
        account_sid = twilio_creds.get("account_sid")
        auth_token = twilio_creds.get("auth_token")

        print("account_sidd", account_sid)
        print("auth_tokenn", auth_token)
        if not account_sid or not auth_token:
            logger.warning("Missing Twilio credentials in DB, cannot resolve to_number")
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

    def _get_telnyx_api_key(self) -> Optional[str]:
        """Fetch Telnyx API key from the DB (service_providers + api_keys)."""
        from core.models.service_provider import ServiceProvider
        from core.models.api_key import ApiKey
        from core.utils.encryption import decrypt

        provider = self.db.query(ServiceProvider).filter(ServiceProvider.name == "telnyx").first()
        if not provider:
            logger.warning("Telnyx service provider not found in DB")
            return None

        api_key = (
            self.db.query(ApiKey)
            .filter(ApiKey.service_provider_id == provider.id, ApiKey.status == "active")
            .first()
        )
        if not api_key:
            logger.warning("No active API key found for Telnyx")
            return None

        return decrypt(api_key.api_key_encrypted)

    async def _fetch_telnyx_to_number(self, call_control_id: str) -> Optional[str]:
        """Fetch the 'to' number for a Telnyx call from Telnyx REST API."""
        api_key = self._get_telnyx_api_key()
        if not api_key:
            logger.warning("Missing Telnyx API key in DB, cannot resolve to_number")
            return None
        url = f"https://api.telnyx.com/v2/calls/{call_control_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning("Telnyx API returned status %s for call %s", response.status, call_control_id)
                        return None
                    data = await response.json()
                    call_data = data.get("data", {})
                    return call_data.get("to")
        except Exception as e:
            logger.error("Error fetching Telnyx call info: %s", e)
            return None

    def _get_exotel_credentials(self, account_sid: str) -> dict:
        """Fetch Exotel credentials from the Channel meta_data for the given account_sid."""
        from core.models.channel import Channel
        from core.models.enums import ChannelType

        channels = (
            self.db.query(Channel)
            .filter(Channel.type == ChannelType.EXOTEL)
            .all()
        )
        for channel in channels:
            meta = channel.meta_data or {}
            if meta.get("account_sid") == account_sid:
                return {
                    "account_sid": meta.get("account_sid"),
                    "api_key": meta.get("api_key"),
                    "api_token": meta.get("api_token"),
                }
        logger.warning("No Exotel channel found for account_sid=%s", account_sid)
        return {}

    async def _fetch_exotel_to_number(self, call_sid: str, account_sid: str) -> Optional[str]:
        """Fetch the 'to' number for an Exotel call from Exotel REST API."""
        creds = self._get_exotel_credentials(account_sid)
        api_key = creds.get("api_key")
        api_token = creds.get("api_token")
        if not api_key or not api_token or not account_sid:
            logger.warning("Missing Exotel credentials in DB, cannot resolve to_number")
            return None
        url = f"https://api.exotel.com/v1/Accounts/{account_sid}/Calls/{call_sid}.json"
        try:
            auth = aiohttp.BasicAuth(api_key, api_token)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth) as response:
                    if response.status != 200:
                        logger.warning("Exotel API returned status %s for call %s", response.status, call_sid)
                        return None
                    data = await response.json()
                    call_details = data.get("Call", {})
                    return call_details.get("To")
        except Exception as e:
            logger.error("Error fetching Exotel call info: %s", e)
            return None

    async def get_to_number_from_call_data_async(
        self, transport_type: str, call_data: Dict[str, Any]
    ) -> Optional[str]:
        """Get the 'to' phone number from parsed call_data (async; handles provider APIs)."""
        if transport_type == "twilio":
            call_sid = call_data.get("call_id")
            if not call_sid:
                return None
            return await self._fetch_twilio_to_number(call_sid)

        elif transport_type == "telnyx":
            # Telnyx provides 'to' directly in WebSocket start message
            to_number = call_data.get("to")
            if to_number:
                return to_number
            # Fallback: fetch from Telnyx REST API using call_control_id
            call_control_id = call_data.get("call_control_id")
            if not call_control_id:
                logger.warning("Telnyx call_data missing both 'to' and 'call_control_id'")
                return None
            return await self._fetch_telnyx_to_number(call_control_id)

        elif transport_type == "exotel":
            # Exotel provides 'to' directly in WebSocket start message
            to_number = call_data.get("to")
            if to_number:
                return to_number
            # Fallback: fetch from Exotel REST API using call_sid and account_sid
            call_sid = call_data.get("call_id")
            account_sid = call_data.get("account_sid")
            if not call_sid or not account_sid:
                logger.warning("Exotel call_data missing both 'to' and 'call_id'/'account_sid'")
                return None
            return await self._fetch_exotel_to_number(call_sid, account_sid)

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
        from pipecat.runner.utils import parse_telephony_websocket

        transport_type, call_data = await parse_telephony_websocket(websocket)
        to_number = await self.get_to_number_from_call_data_async(transport_type, call_data)
        # print("to_number in bot_runner_service.py file ===========", to_number)
        # print("transport_type in bot_runner_service.py file ===========", transport_type)
        # print("call_data in bot_runner_service.py file ===========", call_data)
        if not to_number:
            logger.warning("Could not determine 'to' phone number from call data")
            return None, transport_type, call_data
        agent = self.get_bot_for_phone_number(to_number)
        # print("agent ===========", agent)
        if agent:
            logger.info(
                "Resolved bot for to_number=%s -> agent_id=%s name=%s",
                to_number,
                agent.id,
                agent.name,
            )
        else:
            logger.warning("No agent found for phone number: %s", to_number)
        
        print("agent in bot_runner_service.py file before return ===========", agent.id)
        print("transport_type in bot_runner_service.py file before return ===========", transport_type)
        print("call_data in bot_runner_service.py file before return ===========", call_data)
        return agent, transport_type, call_data
