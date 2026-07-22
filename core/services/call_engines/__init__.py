"""Call-engine registry (outbound origination adapters).

``get_call_engine("twilio", org_id=...)`` returns the provider adapter. Add a new
provider by implementing ``CallEngine`` and wiring it here — mirroring the
philosophy of ``core/services/transport/registry.py``.
"""

from core.services.call_engines.base import CallEngine, CallInfo
from core.services.call_engines.twilio_engine import TwilioCallEngine
from core.services.call_engines.websocket_engine import WebSocketCallEngine


def get_call_engine(provider: str = "twilio", org_id=None) -> CallEngine:
    """Return the ``CallEngine`` for a provider slug, or raise on unknown."""
    if provider == "twilio":
        return TwilioCallEngine(org_id=org_id)
    if provider == "websocket":
        return WebSocketCallEngine(org_id=org_id)
    raise ValueError(f"Unknown call engine provider: {provider}")


__all__ = [
    "CallEngine",
    "CallInfo",
    "TwilioCallEngine",
    "WebSocketCallEngine",
    "get_call_engine",
]
