"""Public telephony WebSocket endpoint — no authentication required.

Telephony providers (Twilio, Telnyx, Exotel, Plivo) connect here to stream
audio for voice agent calls. This EE version reuses the core telephony
endpoint since WebSocket connections from telephony providers do not carry
auth tokens — the agent is resolved by phone number, not by JWT.
"""

from core.api.v1.telephony import router  # noqa: F401
