from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport


class CallDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class CallInfo:
    call_id: str
    session_id: str
    direction: CallDirection
    status: str
    provider: str
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CallTransport(ABC):
    @abstractmethod
    def input(self) -> FrameProcessor:
        ...

    @abstractmethod
    def output(self) -> FrameProcessor:
        ...

    @abstractmethod
    def get_pipecat_transport(self) -> BaseTransport:
        ...

    @abstractmethod
    async def setup(self) -> None:
        ...

    @abstractmethod
    async def teardown(self) -> None:
        ...

    def set_pipeline_task(self, task) -> None:
        return None

    @property
    def audio_sample_rate(self) -> int:
        return 8000

    @property
    def direction(self) -> CallDirection:
        return CallDirection.INBOUND


class CallEngine(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def create_transport(
        self,
        websocket: Any,
        call_data: Dict[str, Any],
        direction: CallDirection = CallDirection.INBOUND,
    ) -> CallTransport:
        ...

    async def initiate_outbound_call(
        self,
        to_number: str,
        from_number: str,
        callback_url: str,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CallInfo:
        raise NotImplementedError(
            f"{self.provider_name} call engine does not implement outbound dialing yet"
        )

    async def end_call(self, call_id: str) -> bool:
        raise NotImplementedError(
            f"{self.provider_name} call engine does not implement end_call yet"
        )

    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.provider_name} call engine does not implement get_call_status yet"
        )

    async def get_recording(self, call_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError(
            f"{self.provider_name} call engine does not implement get_recording yet"
        )
