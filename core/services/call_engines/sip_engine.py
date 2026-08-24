import uuid
from typing import Any, Dict, Optional

from loguru import logger
from pipecat.runner.types import LiveKitRunnerArguments

from core.services.call_engines.base import CallEngine, CallInfo
from core.services.sip.base import SipTerminationError
from core.services.sip.livekit_termination import SIP_ROOM_PREFIX, LiveKitTermination
from core.services.sip.validation import SipConfigError, format_outbound_number

DEFAULT_RING_TIMEOUT = 45


class SipCallEngine(CallEngine):
    def __init__(self, org_id=None, termination: Optional[LiveKitTermination] = None):
        self._org_id = org_id
        self._termination_client = termination

    @property
    def provider_name(self) -> str:
        return "sip"

    def _termination(self) -> LiveKitTermination:
        if self._termination_client is None:
            from core.services.transport.telephony_credentials import channel_config

            self._termination_client = LiveKitTermination(
                channel_config("livekit", org_id=self._org_id)
            )
        return self._termination_client

    def _trunk_for_number(self, from_number: str) -> Dict[str, Any]:
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

            outbound_trunk_id = (trunk.carrier_config or {}).get("outbound_trunk_id")
            if not outbound_trunk_id:
                raise ValueError(
                    f"SIP trunk '{trunk.name}' has no LiveKit outbound trunk — provision it first."
                )
            return {
                "id": str(trunk.id),
                "name": trunk.name,
                "outbound_trunk_id": outbound_trunk_id,
                "tech_prefix": trunk.tech_prefix,
                "outbound_leading_plus_enabled": trunk.outbound_leading_plus_enabled,
                "number_e164_check_enabled": trunk.number_e164_check_enabled,
                "transfer_enabled": trunk.transfer_enabled,
            }

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

        room_name = f"{SIP_ROOM_PREFIX}out-{uuid.uuid4().hex[:12]}"
        attributes = {
            "agent_id": str(agent_id),
            "direction": "outbound",
            "sip.phoneNumber": from_number,
            "sip.trunkPhoneNumber": to_number,
        }
        if scheduled_call_id:
            attributes["scheduled_call_id"] = str(scheduled_call_id)

        logger.info(
            "[outbound] sip dialing agent={} trunk={} from={} to={} room={}",
            agent_id, trunk["id"], from_number, dialed, room_name,
        )

        self._dispatch_bot(room_name, str(agent_id), from_number, to_number, scheduled_call_id)

        try:
            data = self._termination().originate(
                outbound_trunk_id=trunk["outbound_trunk_id"],
                to_number=dialed,
                from_number=from_number,
                room_name=room_name,
                attributes=attributes,
                ringing_timeout=DEFAULT_RING_TIMEOUT,
            )
        except SipTerminationError:
            logger.exception(
                "[outbound] sip originate failed agent={} to={} scheduled_call_id={}",
                agent_id, to_number, scheduled_call_id,
            )
            raise

        logger.info(
            "[outbound] sip call created call_id={} room={} trunk={} scheduled_call_id={}",
            data.get("call_id"), room_name, trunk["id"], scheduled_call_id,
        )
        return CallInfo(
            call_id=data.get("call_id") or room_name,
            session_id=str(scheduled_call_id or agent_id),
            status=data.get("status") or "ringing",
            provider="sip",
        )

    def _dispatch_bot(
        self,
        room_name: str,
        agent_id: str,
        from_number: str,
        to_number: str,
        scheduled_call_id: Optional[str],
    ) -> None:
        import asyncio

        from core.api.sip_routes import _dispatcher

        grant = self._termination().bot_grant(room_name)
        body: Dict[str, Any] = {
            "agent_id": agent_id,
            "transport_type": "livekit",
            "direction": "outbound",
            "call_data": {
                "from": from_number,
                "to": to_number,
                "call_id": room_name,
                "stream_id": room_name,
            },
        }
        if scheduled_call_id:
            body["scheduled_call_id"] = str(scheduled_call_id)

        runner_args = LiveKitRunnerArguments(
            room_name=room_name, url=grant["url"], token=grant["token"], body=body
        )
        asyncio.run(_dispatcher.dispatch(room_name, runner_args))

    def end_call(self, call_id: str) -> bool:
        try:
            self._termination().hangup(call_id, f"caller-{call_id}")
            logger.info("[outbound] sip end_call hung up call_id={}", call_id)
            return True
        except Exception:
            logger.exception("[outbound] sip end_call failed call_id={}", call_id)
            return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        return {"status": None, "duration": None, "price": None, "answered_by": None}

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        raise NotImplementedError(
            "SIP trunk calls are bridged by LiveKit SIP and never fetch TeXML/TwiML."
        )

    def transfer_call(
        self, call_id: str, sip_address: str, headers: Optional[Dict[str, str]] = None
    ) -> bool:
        try:
            self._termination().transfer(call_id, f"caller-{call_id}", sip_address, headers)
            logger.info("[sip] REFER sent room={} to={}", call_id, sip_address)
            return True
        except Exception:
            logger.exception("[sip] REFER failed room={} to={}", call_id, sip_address)
            return False
