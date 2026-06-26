from dataclasses import dataclass


@dataclass(frozen=True)
class RoomGrant:
    room: str
    url: str
    token: str
    identity: str


@dataclass(frozen=True)
class WebRTCSession:
    provider: str
    room: str
    url: str
    token: str
    client_url: str
