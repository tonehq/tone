from typing import Any, Dict, List, Optional

from loguru import logger

from core.services.call_engines.base import CallEngine, CallInfo
from core.services.sip.sbc_client import SbcClient, SbcError
from core.services.sip.validation import (SipConfigError, format_outbound_number,
                                          outbound_gateways, sip_uri)
from core.utils.telephony import default_media_ws_url, pinned_ws_url
from shared.config import settings

DEFAULT_RING_TIMEOUT = 45


class SipCallEngine(CallEngine):
    def __init__(self, org_id=None, sbc: Optional[SbcClient] = None):
        self._org_id = org_id
        self._sbc = sbc or SbcClient()

    @property
    def provider_name(self) -> str:
        return "sip"

    def _trunk_for_number(self, from_number: str):
        from core.database.session import get_db_context
        from core.models.channel import Channel
        from core.models.phone_number import PhoneNumber
        from core.models.sip_trunk import SipTrunk

        with get_db_context() as db:
            query = (
                db.query(SipTrunk)
                .join(Channel, Channel.id == SipTrunk.channel_id)
                .join(PhoneNumber, PhoneNumber.channel_id == Channel.id)
                .filter(PhoneNumber.number == from_number)
            )
            if self._org_id:
                query = query.filter(SipTrunk.organization_id == self._org_id)
            trunk = query.first()
            if trunk is None:
                raise ValueError(
                    f"{from_number} is not attached to a SIP trunk in this organization."
                )
            if not trunk.is_active or not trunk.outbound_enabled:
                raise ValueError(f"SIP trunk '{trunk.name}' is not enabled for outbound calls.")
            return {
                "id": str(trunk.id),
                "name": trunk.name,
                "gateways": trunk.gateways or [],
                "media_encryption": trunk.media_encryption,
                "tech_prefix": trunk.tech_prefix,
                "outbound_leading_plus_enabled": trunk.outbound_leading_plus_enabled,
                "number_e164_check_enabled": trunk.number_e164_check_enabled,
                "sip_diversion_header": trunk.sip_diversion_header,
                "transfer_enabled": trunk.transfer_enabled,
            }

    @staticmethod
    def _destination_uris(trunk: Dict[str, Any], to_number: str) -> List[str]:
        gateways = outbound_gateways(trunk["gateways"])
        if not gateways:
            raise ValueError(f"SIP trunk '{trunk['name']}' has no outbound-enabled gateway.")
        return [sip_uri(to_number, gateway) for gateway in gateways]

    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        agent_id: str,
        callback_base_url: str,
        scheduled_call_id: Optional[str] = None,
    ) -> CallInfo:
        trunk = self._trunk_for_number(from_number)
        try:
            dialed = format_outbound_number(
                to_number,
                e164_check=trunk["number_e164_check_enabled"],
                leading_plus=trunk["outbound_leading_plus_enabled"],
                tech_prefix=trunk["tech_prefix"],
            )
        except SipConfigError as exc:
            raise ValueError(str(exc))

        base = (callback_base_url or settings.BASE_CALL_URL or "").rstrip("/")
        default_ws_url = default_media_ws_url(base)
        if not default_ws_url:
            raise ValueError(
                "BASE_CALL_URL is not set — a SIP call needs a public media WebSocket URL."
            )
        ws_url, pod_name, _, node_name = pinned_ws_url(default_ws_url, "[sip]")

        params: Dict[str, Any] = {
            "agent_id": str(agent_id),
            "direction": "outbound",
            "from": from_number,
            "to": to_number,
            "trunk_id": trunk["id"],
        }
        if scheduled_call_id:
            params["scheduled_call_id"] = str(scheduled_call_id)

        logger.info(
            "[outbound] sip dialing agent={} trunk={} from={} to={} pod={} node={} ws_url={}",
            agent_id, trunk["id"], from_number, dialed, pod_name, node_name, ws_url,
        )
        try:
            data = self._sbc.originate(
                trunk_id=trunk["id"],
                from_number=from_number,
                to_uris=self._destination_uris(trunk, dialed),
                media_ws_url=ws_url,
                params=params,
                media_encryption=trunk["media_encryption"],
                diversion_header=from_number if trunk["sip_diversion_header"] else None,
                timeout_seconds=DEFAULT_RING_TIMEOUT,
            )
        except SbcError:
            logger.exception(
                "[outbound] sip originate failed agent={} to={} scheduled_call_id={}",
                agent_id, to_number, scheduled_call_id,
            )
            raise

        call_id = data.get("call_id") or data.get("id") or ""
        status = data.get("status") or "queued"
        logger.info(
            "[outbound] sip call created call_id={} status={} trunk={} scheduled_call_id={}",
            call_id, status, trunk["id"], scheduled_call_id,
        )
        return CallInfo(
            call_id=call_id,
            session_id=str(scheduled_call_id or agent_id),
            status=status,
            provider="sip",
        )

    def end_call(self, call_id: str) -> bool:
        try:
            self._sbc.hangup(call_id)
            logger.info("[outbound] sip end_call hung up call_id={}", call_id)
            return True
        except Exception:
            logger.exception("[outbound] sip end_call failed call_id={}", call_id)
            return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        data = self._sbc.call_status(call_id)
        return {
            "status": data.get("status"),
            "duration": data.get("duration"),
            "price": None,
            "answered_by": data.get("answered_by"),
        }

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        raise NotImplementedError(
            "SIP trunk calls are bridged by the SBC and never fetch TeXML/TwiML."
        )

    def transfer_call(
        self, call_id: str, sip_address: str, headers: Optional[Dict[str, str]] = None
    ) -> bool:
        try:
            self._sbc.refer(call_id, sip_address, headers)
            logger.info("[sip] REFER sent call_id={} to={}", call_id, sip_address)
            return True
        except Exception:
            logger.exception("[sip] REFER failed call_id={} to={}", call_id, sip_address)
            return False
