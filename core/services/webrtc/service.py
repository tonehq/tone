import uuid
from typing import Any, Optional

from core.services.webrtc.dispatcher import BotDispatcher, LocalBotDispatcher
from core.services.webrtc.registry import build_provider
from core.services.webrtc.session import WebRTCSession

_BOT_IDENTITY = "agent"
_GUEST_IDENTITY = "guest"


class WebRTCSessionService:
    def __init__(self, dispatcher: Optional[BotDispatcher] = None):
        self._dispatcher = dispatcher or LocalBotDispatcher()

    async def start(self, agent: Any, channel_type: str, config: dict) -> WebRTCSession:
        engine = build_provider(channel_type, config)
        room = f"agent-{agent.id}-{uuid.uuid4().hex[:12]}"
        url = await engine.create_room(room)
        guest = await engine.grant(room, url, _GUEST_IDENTITY)
        bot_grant = await engine.grant(room, url, _BOT_IDENTITY)
        body = {"agent_id": str(agent.id), "transport_type": engine.name}
        await self._dispatcher.dispatch(
            room,
            engine.runner_args(bot_grant, body),
            cleanup=lambda: engine.close_room(room),
        )
        return WebRTCSession(
            provider=engine.name,
            room=room,
            url=guest.url,
            token=guest.token,
            client_url=engine.client_url(guest),
        )


_service: Optional[WebRTCSessionService] = None


def webrtc_session_service() -> WebRTCSessionService:
    global _service
    if _service is None:
        _service = WebRTCSessionService()
    return _service
