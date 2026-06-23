from abc import ABC, abstractmethod

from pipecat.runner.types import RunnerArguments

from core.services.webrtc.session import RoomGrant


class WebRTCProvider(ABC):
    name: str

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "WebRTCProvider":
        ...

    @abstractmethod
    async def create_room(self, room: str) -> str:
        ...

    @abstractmethod
    async def grant(self, room: str, url: str, identity: str) -> RoomGrant:
        ...

    @abstractmethod
    def client_url(self, grant: RoomGrant) -> str:
        ...

    @abstractmethod
    async def close_room(self, room: str) -> None:
        ...

    @abstractmethod
    def runner_args(self, grant: RoomGrant, body: dict) -> RunnerArguments:
        ...
