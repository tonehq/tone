from typing import Any, Dict

from loguru import logger

from core.services.sip.base import CarrierProvisionResult, SipCarrier
from core.services.sip.validation import inbound_source_hosts


class GenericSipCarrier(SipCarrier):
    carrier_type = "generic"

    def provision_trunk(self, trunk, credentials: Dict[str, Any]) -> CarrierProvisionResult:
        logger.info("[sip] generic trunk provisioned locally trunk={}", trunk.id)
        return CarrierProvisionResult(
            carrier_ids={"allowlist_hosts": inbound_source_hosts(trunk.gateways)},
            detail=(
                "Generic carrier: point the carrier's origination at the SBC and allowlist "
                "its signalling IPs on their side — Tone has no API to configure for it."
            ),
        )

    def deprovision_trunk(self, trunk, credentials: Dict[str, Any]) -> None:
        return

    def attach_number(self, trunk, credentials: Dict[str, Any], number: str) -> None:
        return

    def detach_number(self, trunk, credentials: Dict[str, Any], number: str) -> None:
        return

    def credential_provider(self):
        return None
