from datetime import timedelta
from urllib.parse import urlencode

from livekit import api
from pipecat.runner.types import LiveKitRunnerArguments

from core.services.webrtc.provider import WebRTCProvider
from core.services.webrtc.session import RoomGrant

_MEET_BASE_URL = "https://meet.livekit.io/custom"
_DEFAULT_TOKEN_TTL = 60 * 60 * 24 * 365


class LiveKitProvider(WebRTCProvider):
    name = "livekit"

    def __init__(self, url: str, api_key: str, api_secret: str, token_ttl: int = _DEFAULT_TOKEN_TTL):
        self._url = url
        self._api_key = api_key
        self._api_secret = api_secret
        self._token_ttl = token_ttl

    @classmethod
    def from_config(cls, config: dict) -> "LiveKitProvider":
        return cls(
            config["url"],
            config["api_key"],
            config["api_secret"],
            token_ttl=int(config.get("token_ttl") or _DEFAULT_TOKEN_TTL),
        )

    async def create_room(self, room: str) -> str:
        return self._url

    async def grant(self, room: str, url: str, identity: str, owner: bool = False) -> RoomGrant:
        token = (
            api.AccessToken(self._api_key, self._api_secret)
            .with_identity(identity)
            .with_name(identity)
            .with_ttl(timedelta(seconds=self._token_ttl))
            .with_grants(api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True))
            .to_jwt()
        )
        return RoomGrant(room=room, url=url, token=token, identity=identity)

    def client_url(self, grant: RoomGrant) -> str:
        query = urlencode({"liveKitUrl": grant.url, "token": grant.token})
        return f"{_MEET_BASE_URL}?{query}"

    async def close_room(self, room: str) -> None:
        http_url = self._url.replace("wss://", "https://").replace("ws://", "http://")
        lkapi = api.LiveKitAPI(http_url, self._api_key, self._api_secret)
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room))
        finally:
            await lkapi.aclose()

    def runner_args(self, grant: RoomGrant, body: dict) -> LiveKitRunnerArguments:
        return LiveKitRunnerArguments(room_name=grant.room, url=grant.url, token=grant.token, body=body)
