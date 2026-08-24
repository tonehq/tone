from typing import Dict, List

from core.services.sip.base import SipCarrier

_CARRIERS: Dict[str, SipCarrier] = {}


def register_carrier(carrier: SipCarrier) -> None:
    _CARRIERS[carrier.carrier_type] = carrier


def get_carrier(carrier_type: str) -> SipCarrier:
    carrier = _CARRIERS.get((carrier_type or "").strip().lower())
    if carrier is None:
        raise ValueError(
            f"Unsupported SIP carrier: {carrier_type}. "
            f"Supported carriers: {', '.join(sorted(_CARRIERS))}"
        )
    return carrier


def supported_carriers() -> List[str]:
    return sorted(_CARRIERS)
