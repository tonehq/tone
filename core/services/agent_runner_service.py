"""Service to get the agent by phone number."""

from typing import Optional

from loguru import logger

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

    def get_agent_by_phone_number(self, phone_number: str) -> Optional[Agent]:
        """Find the agent associated with the given phone number (the number the call came to).

        Uses a single JOIN query instead of separate lookups. Results are cached in
        Redis keyed by phone number.

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
            logger.debug(f"phone_to_agent cache hit: {normalized} -> agent_id={cached_agent_id}")
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
            # Store as a string — the Agent id is a UUID and json.dumps can't serialize it.
            # No TTL: persists until invalidated (phone→agent mapping rarely changes).
            cache_set(cache_key, str(result.id))

        return result

    def get_agent_for_call(self, body: dict) -> Optional[Agent]:
        """The agent for a call: a pre-resolved `body['agent']` (subprocess/warm-pool path),
        a `body['agent_id']` resolved fresh in this session (web-call links), else a lookup
        by the called ('to') number from the parsed telephony call_data.
        Returns None if none resolves."""
        agent = body.get("agent")
        if agent:
            return agent
        agent_id = body.get("agent_id")
        if agent_id:
            return self.db.query(Agent).filter(Agent.id == agent_id).first()
        to_number = (body.get("call_data") or {}).get("to")
        return self.get_agent_by_phone_number(to_number) if to_number else None
