"""Service to resolve the agent for incoming telephony calls by phone number."""

import time as _time
from typing import Any, Dict, Optional, Tuple

import aiohttp
from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.phone_number import PhoneNumber
from core.services.base import BaseService


class AgentRunnerService(BaseService):
    """Resolve the agent for incoming telephony calls by phone number."""

    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number for lookup (strip, optional E.164)."""
        if not phone_number:
            return ""
        return phone_number.strip()

    def get_active_agent_by_id(self, agent_id: Any) -> Optional[Agent]:
        """Return the active Agent for the given id, or None.

        Centralizes agent-by-id resolution so callers (e.g. the /ws/test endpoint)
        don't query the Agent table inline.
        """
        if agent_id is None:
            return None
        return (
            self.db.query(Agent)
            .filter(Agent.id == agent_id, Agent.is_active.is_(True))
            .first()
        )

    def get_phone_number_for_agent(self, agent_id: Any) -> Optional[str]:
        """Return the first phone number mapped to the given agent, or None.

        Reusable counterpart to get_agent_by_phone_number (the reverse direction).
        """
        if agent_id is None:
            return None
        rec = (
            self.db.query(PhoneNumber)
            .filter(PhoneNumber.agent_id == agent_id)
            .first()
        )
        return rec.number if rec else None

    def get_agent_by_phone_number(self, phone_number: str) -> Optional[Agent]:
        """Find the agent associated with the given phone number (the number the call came to).

        Uses a single JOIN query instead of separate lookups.
        Results are cached in Redis keyed by phone number.

        Args:
            phone_number: The 'To' number (our number that received the call).

        Returns:
            The Agent for that phone number, or None if not found.
        """
        from core.services.redis_service import cache_get, cache_set

        normalized = self._normalize_phone_number(phone_number)
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
            .join(PhoneNumber, PhoneNumber.agent_id == Agent.id)
            .filter(PhoneNumber.number == normalized)
            .first()
        )

        if result:
            cache_set(cache_key, result.id, ttl_seconds=1800)

        return result

    def get_agent_for_call(self, body: dict) -> Optional[Agent]:
        """The agent for a call: a pre-resolved `body['agent']` (subprocess/warm-pool path),
        else a lookup by the called ('to') number from the parsed telephony call_data.
        Returns None if neither resolves."""
        agent = body.get("agent")
        if agent:
            return agent
        to_number = (body.get("call_data") or {}).get("to")
        return self.get_agent_by_phone_number(to_number) if to_number else None

    def _channel_config(self, provider_slug: str, channel_id=None) -> dict:
        """Decrypt a telephony Channel's config (encrypted_config) for this org.

        Delegates to the shared `telephony_credentials.channel_config`, reusing this
        service's DB session and org scope so there is a single decryption code path.
        """
        from core.services.transport.telephony_credentials import channel_config

        return channel_config(
            provider_slug, org_id=self.org_id, channel_id=channel_id, db=self.db
        )

    def _get_twilio_credentials_from_channel(self, org_id=None, channel_id=None) -> dict:
        """Fetch Twilio account_sid and auth_token from the org's Twilio channel."""
        cfg = self._channel_config("twilio", channel_id=channel_id)
        account_sid = cfg.get("account_sid")
        auth_token = cfg.get("auth_token")
        if account_sid and auth_token:
            return {"account_sid": account_sid, "auth_token": auth_token}
        return {}

    def _get_twilio_credentials(self, channel_id=None) -> dict:
        """Fetch Twilio credentials from the org's Twilio channel (by channel_id or org)."""
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
        """Fetch the Telnyx API key from the org's Telnyx channel."""
        return self._channel_config("telnyx").get("api_key") or None

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
        """Fetch Exotel credentials from the Exotel channels' encrypted_config by account_sid."""
        from core.models.channel import Channel
        from core.utils.encryption import decrypt_json

        channels = self.db.query(Channel).filter(Channel.channel_type == "exotel").all()
        for channel in channels:
            if not channel.encrypted_config:
                continue
            try:
                meta = decrypt_json(channel.encrypted_config) or {}
            except Exception as e:
                logger.warning("Failed to decrypt exotel channel config: %s", e)
                continue
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

    async def resolve_agent_for_incoming_call(
        self, websocket: Any
    ) -> Tuple[Optional[Agent], str, Dict[str, Any]]:
        """Parse the WebSocket (first messages from /ws), determine the 'to' number, and return the agent for that number.

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
        agent = self.get_agent_by_phone_number(to_number)
        logger.info("[TIMING] get_agent_by_phone_number (+%.3fs)", _time.monotonic() - _t2)

        if agent:
            logger.info(
                "Resolved bot for to_number=%s -> agent_id=%s name=%s",
                to_number,
                agent.id,
                agent.name,
            )
            # Resolve channel_id from the PhoneNumber record for credential lookup
            phone_record = (
                self.db.query(PhoneNumber)
                .filter(PhoneNumber.number == to_number, PhoneNumber.agent_id == agent.id)
                .first()
            )
            if phone_record and phone_record.channel_id:
                call_data["_channel_id"] = phone_record.channel_id
        else:
            logger.warning("No agent found for phone number: %s", to_number)

        return agent, transport_type, call_data
