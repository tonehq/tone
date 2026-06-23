from datetime import datetime, timezone

import httpx
from pipecat.runner.types import DailyRunnerArguments

from core.services.webrtc.provider import WebRTCProvider
from core.services.webrtc.session import RoomGrant

_ROOM_TTL_SECONDS = 60 * 60 * 4


class DailyProvider(WebRTCProvider):
    name = "daily"

    def __init__(self, api_key: str, api_url: str = "https://api.daily.co/v1", room_ttl: int = _ROOM_TTL_SECONDS):
        self._api_key = api_key
        self._api_url = api_url.rstrip("/")
        self._room_ttl = room_ttl

    @classmethod
    def from_config(cls, config: dict) -> "DailyProvider":
        return cls(config["api_key"], config.get("api_url") or "https://api.daily.co/v1")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _now(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    async def create_room(self, room: str) -> str:
        payload = {
            "name": room,
            "privacy": "private",
            "properties": {"exp": self._now() + self._room_ttl, "enable_prejoin_ui": False},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self._api_url}/rooms", json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()["url"]

    async def grant(self, room: str, url: str, identity: str) -> RoomGrant:
        payload = {"properties": {"room_name": room, "user_name": identity}}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self._api_url}/meeting-tokens", json=payload, headers=self._headers())
            response.raise_for_status()
            return RoomGrant(room=room, url=url, token=response.json()["token"], identity=identity)

    def client_url(self, grant: RoomGrant) -> str:
        return f"{grant.url}?t={grant.token}"

    async def close_room(self, room: str) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.delete(f"{self._api_url}/rooms/{room}", headers=self._headers())

    def runner_args(self, grant: RoomGrant, body: dict) -> DailyRunnerArguments:
        return DailyRunnerArguments(room_url=grant.url, token=grant.token, body=body)
