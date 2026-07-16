"""Call engines: provider adapters for outbound-call origination.

A ``CallEngine`` originates and controls an outbound PSTN call through a provider's
REST API (dial, hang up, poll status) and renders the TwiML/answer instructions
that point the answered call at our media WebSocket.

It is **origination-only**. Unlike the tone-test reference this mirrors
(``backend/app/services/call_engines``), havana's engine deliberately omits the
transport-creation and recording methods: the media leg rides havana's existing
``/ws`` + ``TelephonyTransport`` unchanged, and recording is handled by the
pipeline runner. Adding a new provider is just a new subclass registered in
``__init__.py`` — mirroring ``core/services/transport/registry.py``.

Methods are **synchronous**: the Twilio SDK is sync, and the whole call path is
sync (FastAPI ``def`` routes run in the threadpool; Procrastinate tasks are sync),
so async would only add event-loop juggling with no benefit.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CallInfo:
    """Provider-agnostic metadata returned after initiating a call."""

    call_id: str  # provider call id (Twilio Call SID)
    session_id: str  # our linking key — the ``calls.id`` as a string
    status: str  # provider status at creation (e.g. "queued")
    provider: str  # "twilio", ...


class CallEngine(ABC):
    """Provider adapter for outbound call origination + TwiML rendering."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier, e.g. ``"twilio"``."""

    @abstractmethod
    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        agent_id: str,
        callback_base_url: str,
        scheduled_call_id: Optional[str] = None,
    ) -> CallInfo:
        """Place an outbound call. Routing context rides in the TwiML URL query string;
        a status callback is set only for scheduled calls. Raises on provider error /
        missing credentials."""

    @abstractmethod
    def end_call(self, call_id: str) -> bool:
        """Hang up an in-flight call by provider call id. Returns True on success."""

    @abstractmethod
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Fetch current call state from the provider (for webhook-miss reconcile)."""

    @abstractmethod
    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        """Render the answer instructions that bridge the call to ``ws_url`` with the
        given ``<Parameter>`` values (agent_id, direction, from, to, scheduled_call_id)."""
