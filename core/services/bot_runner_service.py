"""Service to resolve the bot (agent) for incoming telephony calls by phone number."""

import time as _time
from typing import Optional, Tuple, Any, Dict

import aiohttp
from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_channel import AgentChannel
from core.models.agent_channel_phone_numbers import AgentChannelPhoneNumbers
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

        Uses a single JOIN query instead of separate lookups.
        Results are cached in Redis keyed by phone number.

        Args:
            phone_number: The 'To' number (our number that received the call).

        Returns:
            The Agent for that phone number, or None if not found.
        """
        from core.services.redis_service import cache_get, cache_set

        normalized = self._normalize_phone_number(phone_number)
        print("normalized in bot_runner_service.py file ===========", normalized)
        if not normalized:
            return None

        # Check Redis cache first
        cache_key = f"phone_to_agent:{normalized}"
        cached_agent_id = cache_get(cache_key)
        if cached_agent_id is not None:
            logger.info("[TIMING] phone_to_agent CACHE HIT: %s -> agent_id=%s", normalized, cached_agent_id)
            agent = self.db.query(Agent).filter(Agent.id == cached_agent_id).first()
            if agent:
                return agent

        # Single JOIN: phone_number → agent (avoids 2 separate queries)
        result = (
            self.db.query(Agent)
            .join(AgentChannelPhoneNumbers, AgentChannelPhoneNumbers.agent_id == Agent.id)
            .filter(AgentChannelPhoneNumbers.phone_number == normalized)
            .first()
        )
        if not result:
            # Fallback to channel-based lookup for legacy records without agent_id
            result = (
                self.db.query(Agent)
                .join(AgentChannel, AgentChannel.agent_id == Agent.id)
                .join(AgentChannelPhoneNumbers, AgentChannelPhoneNumbers.channel_id == AgentChannel.channel_id)
                .filter(AgentChannelPhoneNumbers.phone_number == normalized)
                .first()
            )

        if result:
            cache_set(cache_key, result.id, ttl_seconds=1800)

        return result

    def _get_twilio_credentials_from_channel(self, org_id=None, channel_id=None) -> dict:
        """Fetch Twilio account_sid and auth_token from the channels table.

        If channel_id is provided, looks up that specific channel.
        Otherwise falls back to org-scoped type-based lookup.
        Falls back to _get_twilio_credentials_from_api_keys() if no channel found.
        """
        from core.models.channel import Channel
        from core.models.enums import ChannelType

        if channel_id:
            channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
            if channel and channel.meta_data:
                meta = channel.meta_data
                account_sid = meta.get("account_sid")
                auth_token = meta.get("auth_token")
                if account_sid and auth_token:
                    return {"account_sid": account_sid, "auth_token": auth_token}

        if org_id:
            channel = (
                self.db.query(Channel)
                .filter(Channel.type == ChannelType.TWILIO, Channel.organization_id == org_id)
                .first()
            )
            if channel and channel.meta_data:
                meta = channel.meta_data
                account_sid = meta.get("account_sid")
                auth_token = meta.get("auth_token")
                if account_sid and auth_token:
                    return {"account_sid": account_sid, "auth_token": auth_token}

        # Fallback: try api_keys table
        return self._get_twilio_credentials_from_api_keys()

    def _get_twilio_credentials_from_api_keys(self) -> dict:
        """Fetch Twilio account_sid and auth_token from the DB (api_keys table).

        Legacy method — queries globally without org scoping.
        """
        from core.models.service_provider import ServiceProvider
        from core.models.api_key import ApiKey
        from core.utils.encryption import decrypt

        provider = self.db.query(ServiceProvider).filter(ServiceProvider.name == "twilio").first()
        if not provider:
            logger.warning("Twilio service provider not found in DB")
            return {}

        q = self.db.query(ApiKey).filter(ApiKey.service_provider_id == provider.id)
        if self.org_id:
            q = q.filter(ApiKey.organization_id == self.org_id)
        api_keys = q.all()

        creds = {}
        for ak in api_keys:
            additional = ak.additional_credentials or {}
            key_type = additional.get("key_type")
            if key_type == "account_sid":
                creds["account_sid"] = decrypt(ak.api_key_encrypted)
            if key_type == "auth_token":
                creds["auth_token"] = decrypt(ak.api_key_encrypted)

        return creds

    def _get_twilio_credentials(self, channel_id=None) -> dict:
        """Fetch Twilio credentials — tries channel_id first, then org-scoped, then api_keys."""
        return self._get_twilio_credentials_from_channel(org_id=self.org_id, channel_id=channel_id)

    async def _fetch_twilio_call_info(self, call_sid: str, call_data: Dict[str, Any], channel_id=None) -> Optional[str]:
        """Fetch call info from Twilio REST API and enrich call_data with from/to and credentials.

        Stores 'from', 'to', and '_twilio_creds' into call_data so downstream code
        (bot.py, _create_serializer) can reuse them without duplicate DB/API calls.
        Returns the 'to' number or None.
        """
        twilio_creds = self._get_twilio_credentials(channel_id=channel_id)
        account_sid = twilio_creds.get("account_sid")
        auth_token = twilio_creds.get("auth_token")

        # Cache credentials in call_data for reuse by _create_serializer
        call_data["_twilio_creds"] = twilio_creds

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
                    to_number = data.get("to")
                    from_number = data.get("from")
                    # Store both numbers so bot() doesn't need to call Twilio API again
                    if to_number:
                        call_data["to"] = to_number
                    if from_number:
                        call_data["from"] = from_number
                    return to_number
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

        q = self.db.query(ApiKey).filter(ApiKey.service_provider_id == provider.id, ApiKey.status == "active")
        if self.org_id:
            q = q.filter(ApiKey.organization_id == self.org_id)
        api_key = q.first()
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
            # Use from/to from Twilio's WebSocket body if available (avoids 6-7s API call)
            body = call_data.get("body") or {}
            to_number = body.get("to") or call_data.get("to")
            from_number = body.get("from") or call_data.get("from")
            if to_number:
                call_data["to"] = to_number
                if from_number:
                    call_data["from"] = from_number
                return to_number
            # Fallback: call Twilio REST API if not in body
            call_sid = call_data.get("call_id")
            if not call_sid:
                return None
            return await self._fetch_twilio_call_info(call_sid, call_data, channel_id=call_data.get("_channel_id"))

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

        _t0 = _time.monotonic()
        transport_type, call_data = await parse_telephony_websocket(websocket)
        logger.info("[TIMING] parse_telephony_websocket (+%.3fs)", _time.monotonic() - _t0)

        _t1 = _time.monotonic()
        to_number = await self.get_to_number_from_call_data_async(transport_type, call_data)
        logger.info("[TIMING] get_to_number_from_call_data_async (+%.3fs)", _time.monotonic() - _t1)

        if not to_number:
            logger.warning("Could not determine 'to' phone number from call data")
            return None, transport_type, call_data

        _t2 = _time.monotonic()
        agent = self.get_bot_for_phone_number(to_number)
        logger.info("[TIMING] get_bot_for_phone_number (+%.3fs)", _time.monotonic() - _t2)

        if agent:
            logger.info(
                "Resolved bot for to_number=%s -> agent_id=%s name=%s",
                to_number,
                agent.id,
                agent.name,
            )
            # Resolve channel_id from AgentChannelPhoneNumbers for credential lookup
            phone_record = (
                self.db.query(AgentChannelPhoneNumbers)
                .filter(AgentChannelPhoneNumbers.phone_number == to_number, AgentChannelPhoneNumbers.agent_id == agent.id)
                .first()
            )
            if phone_record and phone_record.channel_id:
                call_data["_channel_id"] = phone_record.channel_id
        else:
            logger.warning("No agent found for phone number: %s", to_number)

        return agent, transport_type, call_data
