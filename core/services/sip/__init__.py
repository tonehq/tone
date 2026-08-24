from core.services.sip.base import (CarrierProvisionResult, SipCarrier,
                                    SipCarrierError)
from core.services.sip.generic_carrier import GenericSipCarrier
from core.services.sip.registry import (get_carrier, register_carrier,
                                        supported_carriers)
from core.services.sip.sbc_client import SbcClient, SbcError
from core.services.sip.validation import SipConfigError
from core.services.sip.telnyx_carrier import TelnyxSipCarrier
from core.services.sip.trunk_service import SIP_CHANNEL_TYPE, SipTrunkService

register_carrier(TelnyxSipCarrier())
register_carrier(GenericSipCarrier())

__all__ = [
    "CarrierProvisionResult",
    "GenericSipCarrier",
    "SIP_CHANNEL_TYPE",
    "SbcClient",
    "SbcError",
    "SipCarrier",
    "SipCarrierError",
    "SipConfigError",
    "SipTrunkService",
    "TelnyxSipCarrier",
    "get_carrier",
    "register_carrier",
    "supported_carriers",
]
