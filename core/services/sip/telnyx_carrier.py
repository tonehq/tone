from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from core.services.sip.base import (CarrierProvisionResult, SipCarrier, SipCarrierError,
                                    TerminationEndpoint)
from core.services.sip.validation import default_port, inbound_source_hosts

TELNYX_API_BASE = "https://api.telnyx.com/v2"
HTTP_TIMEOUT = 20


class TelnyxSipCarrier(SipCarrier):
    carrier_type = "telnyx"

    def _request(
        self,
        method: str,
        path: str,
        credentials: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        api_key = (credentials or {}).get("api_key")
        if not api_key:
            raise SipCarrierError(
                "No Telnyx API key configured for this organization. "
                "Add a Telnyx channel before provisioning a SIP trunk."
            )
        url = f"{TELNYX_API_BASE}{path}"
        try:
            response = requests.request(
                method,
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                params=params,
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.HTTPError:
            logger.exception("[sip] telnyx {} {} failed", method, path)
            raise SipCarrierError(self._error_detail(response))
        except requests.RequestException as exc:
            logger.exception("[sip] telnyx {} {} unreachable", method, path)
            raise SipCarrierError(f"Telnyx API is unreachable: {exc}")

    @staticmethod
    def _error_detail(response) -> str:
        try:
            errors = response.json().get("errors") or []
        except ValueError:
            errors = []
        if errors:
            first = errors[0]
            return f"Telnyx API error: {first.get('detail') or first.get('title')}"
        return f"Telnyx API error (HTTP {response.status_code})"

    @staticmethod
    def _connection_transport(trunk) -> str:
        for gateway in trunk.gateways or []:
            if gateway.get("inbound_enabled", True):
                return str(gateway.get("transport") or "udp").upper()
        return "UDP"

    @staticmethod
    def _resource_name(trunk) -> str:
        return f"tone-{trunk.name}-{str(trunk.id)[:8]}"

    def _find_by_name(
        self, path: str, credentials: Dict[str, Any], name_field: str, name: str
    ) -> str:
        try:
            data = self._request(
                "GET", path, credentials, params={f"filter[{name_field}][contains]": name}
            )
        except SipCarrierError:
            return ""
        for row in data.get("data") or []:
            if row.get(name_field) == name:
                return row.get("id", "")
        return ""

    def _ensure_outbound_voice_profile(self, trunk, credentials: Dict[str, Any]) -> str:
        existing = (trunk.carrier_config or {}).get(
            "outbound_voice_profile_id"
        ) or self._find_by_name(
            "/outbound_voice_profiles", credentials, "name", self._resource_name(trunk)
        )
        if existing:
            return existing
        data = self._request(
            "POST",
            "/outbound_voice_profiles",
            credentials,
            payload={
                "name": self._resource_name(trunk),
                "traffic_type": "conversational",
                "service_plan": "global",
                "enabled": True,
            },
        )
        return data.get("data", {}).get("id", "")

    def _ensure_connection(self, trunk, credentials: Dict[str, Any]) -> str:
        payload: Dict[str, Any] = {
            "connection_name": self._resource_name(trunk),
            "transport_protocol": self._connection_transport(trunk),
            "active": bool(trunk.is_active),
            "inbound": {"ani_number_format": "+E.164", "dnis_number_format": "+e164"},
        }
        if trunk.media_encryption == "srtp":
            payload["encrypted_media"] = "SRTP"

        connection_id = (trunk.carrier_config or {}).get("connection_id") or self._find_by_name(
            "/fqdn_connections", credentials, "connection_name", self._resource_name(trunk)
        )
        if connection_id:
            self._request("PATCH", f"/fqdn_connections/{connection_id}", credentials, payload=payload)
            return connection_id
        data = self._request("POST", "/fqdn_connections", credentials, payload=payload)
        return data.get("data", {}).get("id", "")

    def _assign_outbound_profile(
        self, credentials: Dict[str, Any], connection_id: str, outbound_voice_profile_id: str
    ) -> None:
        self._request(
            "PATCH",
            f"/fqdn_connections/{connection_id}",
            credentials,
            payload={"outbound": {"outbound_voice_profile_id": outbound_voice_profile_id}},
        )

    def _ensure_fqdn(
        self, trunk, credentials: Dict[str, Any], connection_id: str,
        termination: TerminationEndpoint,
    ) -> str:
        termination_fqdn = (termination.host or "").strip()
        if not termination_fqdn:
            raise SipCarrierError(
                "No SIP termination host resolved — configure a LiveKit channel "
                "(url + api_key + api_secret) or set SIP_TERMINATION_FQDN."
            )
        transport = self._connection_transport(trunk).lower()
        port = termination.port or default_port(transport)
        fqdn_id = (trunk.carrier_config or {}).get("fqdn_id")
        payload = {
            "connection_id": connection_id,
            "fqdn": termination_fqdn,
            "port": port,
            "dns_record_type": "a",
        }
        if fqdn_id:
            self._request("PATCH", f"/fqdns/{fqdn_id}", credentials, payload=payload)
            return fqdn_id
        data = self._request("POST", "/fqdns", credentials, payload=payload)
        return data.get("data", {}).get("id", "")

    def provision_trunk(
        self, trunk, credentials: Dict[str, Any], termination: TerminationEndpoint
    ) -> CarrierProvisionResult:
        connection_id = self._ensure_connection(trunk, credentials)
        fqdn_id = self._ensure_fqdn(trunk, credentials, connection_id, termination)
        outbound_voice_profile_id = self._ensure_outbound_voice_profile(trunk, credentials)

        outbound_profile_attached = True
        try:
            self._assign_outbound_profile(credentials, connection_id, outbound_voice_profile_id)
        except SipCarrierError as exc:
            outbound_profile_attached = False
            logger.warning(
                "[sip] telnyx outbound profile attach deferred trunk={} connection={}: {}",
                trunk.id, connection_id, exc,
            )
            attach_warning = (
                f"Outbound profile not attached yet: {exc} "
                f"(the termination host {termination.host} must resolve publicly before "
                f"Telnyx will attach the profile — re-provision once it does)"
            )

        notes = []
        if not outbound_profile_attached:
            notes.append(attach_warning)
        if trunk.auth_mode == "digest":
            notes.append(
                "Telnyx FQDN connections authenticate by FQDN/IP; the digest credentials "
                "are enforced by the SBC on inbound INVITEs only."
            )
        detail = " | ".join(notes)
        logger.info(
            "[sip] telnyx trunk provisioned trunk={} connection={} fqdn={} ovp={}",
            trunk.id, connection_id, fqdn_id, outbound_voice_profile_id,
        )
        return CarrierProvisionResult(
            carrier_ids={
                "connection_id": connection_id,
                "fqdn_id": fqdn_id,
                "outbound_voice_profile_id": outbound_voice_profile_id,
                "allowlist_hosts": inbound_source_hosts(trunk.gateways),
            },
            detail=detail,
        )

    def deprovision_trunk(self, trunk, credentials: Dict[str, Any]) -> None:
        carrier_config = trunk.carrier_config or {}
        for path in (
            f"/fqdns/{carrier_config.get('fqdn_id')}" if carrier_config.get("fqdn_id") else None,
            f"/fqdn_connections/{carrier_config.get('connection_id')}"
            if carrier_config.get("connection_id")
            else None,
            f"/outbound_voice_profiles/{carrier_config.get('outbound_voice_profile_id')}"
            if carrier_config.get("outbound_voice_profile_id")
            else None,
        ):
            if not path:
                continue
            try:
                self._request("DELETE", path, credentials)
            except SipCarrierError:
                logger.exception("[sip] telnyx deprovision step failed trunk={} path={}", trunk.id, path)

    def _number_id(self, credentials: Dict[str, Any], number: str) -> str:
        data = self._request(
            "GET", "/phone_numbers", credentials, params={"filter[phone_number]": number}
        )
        rows = data.get("data") or []
        if not rows:
            raise SipCarrierError(f"{number} is not a phone number on this Telnyx account.")
        return rows[0].get("id", "")

    def attach_number(self, trunk, credentials: Dict[str, Any], number: str) -> None:
        connection_id = (trunk.carrier_config or {}).get("connection_id")
        if not connection_id:
            raise SipCarrierError("Provision the trunk before attaching numbers to it.")
        number_id = self._number_id(credentials, number)
        self._request(
            "PATCH",
            f"/phone_numbers/{number_id}",
            credentials,
            payload={"connection_id": connection_id},
        )
        logger.info("[sip] telnyx number attached trunk={} number={}", trunk.id, number)

    def detach_number(self, trunk, credentials: Dict[str, Any], number: str) -> None:
        number_id = self._number_id(credentials, number)
        self._request(
            "PATCH", f"/phone_numbers/{number_id}", credentials, payload={"connection_id": ""}
        )
        logger.info("[sip] telnyx number detached trunk={} number={}", trunk.id, number)

    def list_numbers(self, trunk, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = self._request(
            "GET", "/phone_numbers", credentials, params={"page[size]": 250}
        )
        return [
            {
                "id": row.get("id"),
                "number": row.get("phone_number"),
                "label": row.get("customer_reference") or row.get("connection_name"),
            }
            for row in data.get("data") or []
            if row.get("phone_number")
        ]
