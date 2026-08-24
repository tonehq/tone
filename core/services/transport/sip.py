from typing import Any, Dict, Optional
from uuid import uuid4

from core.serializers.raw_pcm import RawPCMSerializer
from core.services.sip.validation import DEFAULT_SIP_SAMPLE_RATE
from core.services.transport.base import TelephonyProvider

SIP_TRANSPORT_TYPE = "sip"


class SipTransport(TelephonyProvider):
    transport_type = SIP_TRANSPORT_TYPE

    def create_serializer(self, call_data: dict):
        sample_rate = int((call_data or {}).get("sample_rate") or DEFAULT_SIP_SAMPLE_RATE)
        return RawPCMSerializer(sample_rate=sample_rate, num_channels=1)


def build_sip_call_body(query_params) -> Optional[Dict[str, Any]]:
    if (query_params.get("transport_type") or "").strip().lower() != SIP_TRANSPORT_TYPE:
        return None

    def _param(name: str) -> str:
        return (query_params.get(name) or "").strip()

    try:
        sample_rate = int(_param("sample_rate") or DEFAULT_SIP_SAMPLE_RATE)
    except (TypeError, ValueError):
        sample_rate = DEFAULT_SIP_SAMPLE_RATE

    agent_id = _param("agent_id")
    params: Dict[str, Any] = {}
    for key in ("agent_id", "direction", "scheduled_call_id"):
        value = _param(key)
        if value:
            params[key] = value

    call_data: Dict[str, Any] = {
        "from": _param("from"),
        "to": _param("to"),
        "body": params,
        "stream_id": _param("call_id") or uuid4().hex,
        "call_id": _param("call_id") or uuid4().hex,
        "sample_rate": sample_rate,
        "sip_trunk_id": _param("trunk_id"),
    }

    body: Dict[str, Any] = {
        "transport_type": SIP_TRANSPORT_TYPE,
        "call_data": call_data,
    }
    if agent_id:
        body["agent_id"] = agent_id
    return body
