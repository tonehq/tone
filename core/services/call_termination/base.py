"""Runtime call-termination strategies.

A ``CallTerminator`` hangs up an IN-PROGRESS media call at pipeline teardown by
calling the provider's REST hangup API directly. This is the authoritative,
provider-agnostic hangup our runner owns — independent of the Pipecat serializer's
``auto_hang_up``, which fires only if an End/Cancel frame reaches the serializer
before the socket dies (see pipecat-ai/pipecat#728) and which some providers
(e.g. Exotel) don't implement at all.

Distinct from ``core/services/call_engines`` (outbound *origination*): a terminator
resolves the hangup id from the LIVE ``call_data`` the transport parsed at answer
time (Twilio Call SID, Telnyx ``call_control_id``) and drops that leg. Add a
provider by implementing this ABC and registering it in ``__init__.py`` — mirroring
``core/services/transport/registry.py`` and ``core/services/call_engines``.
"""

from abc import ABC, abstractmethod
from typing import Optional


class CallTerminator(ABC):
    """Provider adapter that hangs up a live media call."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier, e.g. ``"twilio"``."""

    @abstractmethod
    async def hangup(self, call_data: dict, org_id: Optional[str]) -> bool:
        """Drop the live call, resolving the provider hangup id from ``call_data``.

        Returns ``True`` on a confirmed hangup — a provider "call already ended"
        response counts as success. The orchestrator ``terminate_call`` runs this
        best-effort and swallows/logs any exception, so implementations may raise
        on a genuinely unexpected error rather than hiding it.
        """
