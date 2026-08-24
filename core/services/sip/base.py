from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class SipCarrierError(RuntimeError):
    pass


class SipTerminationError(RuntimeError):
    pass


@dataclass
class TerminationEndpoint:
    host: str = ""
    port: int = 0


@dataclass
class CarrierProvisionResult:
    carrier_ids: Dict[str, Any] = field(default_factory=dict)
    detail: str = ""


class SipCarrier(ABC):
    carrier_type: str = ""

    @abstractmethod
    def provision_trunk(
        self,
        trunk,
        credentials: Dict[str, Any],
        termination: TerminationEndpoint,
        auth: Optional[Dict[str, str]] = None,
    ) -> CarrierProvisionResult:
        ...

    @abstractmethod
    def deprovision_trunk(self, trunk, credentials: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def attach_number(self, trunk, credentials: Dict[str, Any], number: str) -> None:
        ...

    @abstractmethod
    def detach_number(self, trunk, credentials: Dict[str, Any], number: str) -> None:
        ...

    def list_numbers(self, trunk, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def credential_provider(self) -> Optional[str]:
        return self.carrier_type
