from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.models.channel import Channel
from core.models.phone_number import PhoneNumber
from core.models.sip_trunk import SipTrunk
from core.services.base import BaseService
from core.services.sip import validation
from core.services.sip.base import SipCarrierError
from core.services.sip.registry import get_carrier, supported_carriers
from core.services.sip.sbc_client import SbcClient, SbcError
from core.services.transport.telephony_credentials import channel_config
from core.utils.auth_helpers import coerce_uuid
from core.utils.encryption import decrypt_json, encrypt_json
from shared.config import settings

SIP_CHANNEL_TYPE = "sip"

def trunk_auth(record) -> Dict[str, Any]:
    return decrypt_json(record.encrypted_auth) if record.encrypted_auth else {}


STATUS_DRAFT = "draft"
STATUS_PROVISIONED = "provisioned"
STATUS_ERROR = "error"


class SipTrunkService(BaseService):
    def __init__(self, db, user_id=None, org_id=None, sbc: Optional[SbcClient] = None):
        super().__init__(db, user_id=user_id, org_id=org_id)
        self._sbc = sbc or SbcClient()

    def list_trunks(self) -> List[Dict[str, Any]]:
        rows = self.query(SipTrunk).order_by(SipTrunk.updated_at.desc()).all()
        return [self._response(row) for row in rows]

    def get_trunk(
        self, trunk_id: Union[str, UUID], include_auth: bool = False
    ) -> Dict[str, Any]:
        return self._response(self._get_record(trunk_id), include_auth=include_auth)

    @staticmethod
    def _response(record: SipTrunk, include_auth: bool = False) -> Dict[str, Any]:
        payload = {
            **record.to_dict(),
            "termination_host": validation.termination_host(record.id),
            "inbound_uri_template": validation.inbound_uri_template(record.id),
        }
        if include_auth:
            auth = trunk_auth(record)
            payload["auth"] = {
                "auth_username": auth.get("auth_username") or record.auth_username or "",
                "auth_password": auth.get("auth_password") or "",
                "register_server": auth.get("register_server") or "",
            }
        return payload

    def create_trunk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        name = (data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")

        carrier = (data.get("carrier") or "telnyx").strip().lower()
        if carrier not in supported_carriers():
            raise HTTPException(
                status_code=400,
                detail=f"carrier must be one of {', '.join(supported_carriers())}",
            )

        channel = Channel(
            organization_id=self.org_id,
            name=name,
            channel_type=SIP_CHANNEL_TYPE,
            encrypted_config=encrypt_json({"carrier": carrier}),
        )
        self.db.add(channel)
        self.db.flush()

        record = SipTrunk(
            organization_id=self.org_id,
            name=name,
            carrier=carrier,
            channel_id=channel.id,
            status=STATUS_DRAFT,
        )
        self._apply_payload(record, data)
        self.db.add(record)
        self._commit("A SIP trunk with this name already exists")
        self.db.refresh(record)

        channel.encrypted_config = encrypt_json(
            {"carrier": carrier, "sip_trunk_id": str(record.id)}
        )
        self.db.commit()

        logger.info("[sip] trunk created id={} carrier={} org={}", record.id, carrier, self.org_id)
        return self._response(record)

    def update_trunk(self, trunk_id: Union[str, UUID], data: Dict[str, Any]) -> Dict[str, Any]:
        record = self._get_record(trunk_id)
        name = (data.get("name") or "").strip()
        if name:
            record.name = name
        self._apply_payload(record, data)

        channel = self.db.query(Channel).filter(Channel.id == record.channel_id).first()
        if channel is not None and name:
            channel.name = name

        self._commit("A SIP trunk with this name already exists")
        self.db.refresh(record)
        logger.info("[sip] trunk updated id={}", record.id)
        return self._response(record)

    def delete_trunk(self, trunk_id: Union[str, UUID]) -> Dict[str, str]:
        record = self._get_record(trunk_id)
        attached = (
            self.query(PhoneNumber).filter(PhoneNumber.channel_id == record.channel_id).count()
        )
        if attached:
            raise HTTPException(
                status_code=409,
                detail=f"Detach the {attached} phone number(s) on this trunk before deleting it.",
            )

        credentials = self._carrier_credentials(record)
        try:
            get_carrier(record.carrier).deprovision_trunk(record, credentials)
        except SipCarrierError:
            logger.exception("[sip] carrier deprovision failed trunk={}", record.id)

        if self._sbc.configured:
            try:
                self._sbc.remove_trunk(str(record.id))
            except SbcError:
                logger.exception("[sip] sbc trunk removal failed trunk={}", record.id)

        channel_id = record.channel_id
        self.db.delete(record)
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if channel is not None:
            self.db.delete(channel)
        self.db.commit()
        logger.info("[sip] trunk deleted id={}", trunk_id)
        return {"message": "SIP trunk deleted successfully"}

    def provision_trunk(self, trunk_id: Union[str, UUID]) -> Dict[str, Any]:
        record = self._get_record(trunk_id)
        credentials = self._carrier_credentials(record)
        try:
            result = get_carrier(record.carrier).provision_trunk(record, credentials)
            record.carrier_config = {**(record.carrier_config or {}), **result.carrier_ids}
            self._sync_to_sbc(record)
            record.status = STATUS_PROVISIONED
            record.status_detail = result.detail or None
        except (SipCarrierError, SbcError) as exc:
            record.status = STATUS_ERROR
            record.status_detail = str(exc)[:500]
            self.db.commit()
            logger.exception("[sip] trunk provisioning failed id={}", record.id)
            raise HTTPException(status_code=502, detail=str(exc))

        self.db.commit()
        self.db.refresh(record)
        logger.info("[sip] trunk provisioned id={} carrier={}", record.id, record.carrier)
        return self._response(record)

    def attach_number(
        self, trunk_id: Union[str, UUID], number: str, label: Optional[str] = None
    ) -> Dict[str, Any]:
        record = self._get_record(trunk_id)
        normalized = (number or "").strip().replace(" ", "")
        if record.number_e164_check_enabled and not validation.is_e164(normalized):
            raise HTTPException(
                status_code=400, detail=f"'{number}' must be an E.164 number (e.g. +14155550123)."
            )

        existing = (
            self.query(PhoneNumber).filter(PhoneNumber.number == normalized).first()
        )
        if existing is not None and existing.channel_id != record.channel_id:
            raise HTTPException(
                status_code=409,
                detail="This number is already attached to another channel in this organization.",
            )

        try:
            get_carrier(record.carrier).attach_number(
                record, self._carrier_credentials(record), normalized
            )
        except SipCarrierError as exc:
            logger.exception("[sip] carrier number attach failed trunk={} number={}", record.id, normalized)
            raise HTTPException(status_code=502, detail=str(exc))

        if existing is None:
            existing = PhoneNumber(
                organization_id=self.org_id,
                number=normalized,
                channel_id=record.channel_id,
                label=label,
            )
            self.db.add(existing)
        elif label:
            existing.label = label
        self.db.commit()
        self.db.refresh(existing)

        logger.info("[sip] number attached trunk={} number={}", record.id, normalized)
        return {
            "id": str(existing.id),
            "number": existing.number,
            "label": existing.label,
            "channel_id": str(existing.channel_id),
            "sip_trunk_id": str(record.id),
        }

    def detach_number(self, trunk_id: Union[str, UUID], number: str) -> Dict[str, str]:
        record = self._get_record(trunk_id)
        normalized = (number or "").strip().replace(" ", "")
        row = (
            self.query(PhoneNumber)
            .filter(
                PhoneNumber.number == normalized,
                PhoneNumber.channel_id == record.channel_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Number is not attached to this trunk.")

        try:
            get_carrier(record.carrier).detach_number(
                record, self._carrier_credentials(record), normalized
            )
        except SipCarrierError:
            logger.exception("[sip] carrier number detach failed trunk={} number={}", record.id, normalized)

        self.db.delete(row)
        self.db.commit()
        logger.info("[sip] number detached trunk={} number={}", record.id, normalized)
        return {"message": "Number detached from trunk"}

    def list_carrier_numbers(self, trunk_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        record = self._get_record(trunk_id)
        try:
            return get_carrier(record.carrier).list_numbers(
                record, self._carrier_credentials(record)
            )
        except SipCarrierError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    def get_trunk_record(self, trunk_id: Union[str, UUID]) -> SipTrunk:
        return self._get_record(trunk_id)

    def trunk_for_channel(self, channel_id: Union[str, UUID]) -> SipTrunk:
        record = (
            self.query(SipTrunk)
            .filter(SipTrunk.channel_id == coerce_uuid(channel_id))
            .first()
        )
        if record is None:
            raise HTTPException(status_code=404, detail="SIP trunk not found for this channel.")
        return record

    def _apply_payload(self, record: SipTrunk, data: Dict[str, Any]) -> None:
        try:
            if "gateways" in data:
                record.gateways = validation.normalize_gateways(data.get("gateways"))
            if "inbound_enabled" in data:
                record.inbound_enabled = bool(data.get("inbound_enabled"))
            if "outbound_enabled" in data:
                record.outbound_enabled = bool(data.get("outbound_enabled"))
            if "auth_mode" in data:
                record.auth_mode = validation.normalize_auth_mode(data.get("auth_mode"))
            if "media_encryption" in data:
                record.media_encryption = validation.normalize_media_encryption(
                    data.get("media_encryption")
                )
            if "tech_prefix" in data:
                record.tech_prefix = validation.normalize_tech_prefix(data.get("tech_prefix"))
            for flag in (
                "register_enabled",
                "sip_diversion_header",
                "outbound_leading_plus_enabled",
                "number_e164_check_enabled",
                "transfer_enabled",
                "is_active",
            ):
                if flag in data:
                    setattr(record, flag, bool(data.get(flag)))

            if "auth" in data or "auth_mode" in data:
                username, auth = validation.normalize_auth(
                    data.get("auth"), record.auth_mode, trunk_auth(record)
                )
                record.auth_username = username
                record.encrypted_auth = encrypt_json(auth) if auth else None

            validation.validate_gateway_coverage(
                record.gateways or [], record.inbound_enabled, record.outbound_enabled
            )
        except validation.SipConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    def _sync_to_sbc(self, record: SipTrunk) -> None:
        if not self._sbc.configured:
            raise SbcError(
                "SIP_SBC_CONTROL_URL is not set — provision the SBC before activating a trunk."
            )
        self._sbc.sync_trunk(self.sbc_payload(record))

    def sbc_payload(self, record: SipTrunk) -> Dict[str, Any]:
        auth = trunk_auth(record)
        base_url = (settings.BASE_CALL_URL or "").rstrip("/")
        return {
            "trunk_id": str(record.id),
            "organization_id": str(record.organization_id),
            "name": record.name,
            "carrier": record.carrier,
            "active": bool(record.is_active),
            "inbound": {
                "enabled": bool(record.inbound_enabled),
                "auth_mode": record.auth_mode,
                "auth_username": auth.get("auth_username") or "",
                "auth_password": auth.get("auth_password") or "",
                "allowed_hosts": validation.inbound_source_hosts(record.gateways),
                "termination_host": validation.termination_host(record.id),
            },
            "outbound": {
                "enabled": bool(record.outbound_enabled),
                "gateways": validation.outbound_gateways(record.gateways),
                "tech_prefix": record.tech_prefix or "",
                "leading_plus_enabled": bool(record.outbound_leading_plus_enabled),
                "diversion_header_enabled": bool(record.sip_diversion_header),
                "register_enabled": bool(record.register_enabled),
                "register_server": auth.get("register_server") or "",
            },
            "media": {
                "encryption": record.media_encryption,
                "sample_rate": validation.DEFAULT_SIP_SAMPLE_RATE,
            },
            "transfer_enabled": bool(record.transfer_enabled),
            "control": {
                "route_url": f"{base_url}/sip/inbound" if base_url else "",
                "status_url": f"{base_url}/sip/status" if base_url else "",
                "token": settings.SIP_SBC_WEBHOOK_TOKEN or "",
            },
        }

    def _carrier_credentials(self, record: SipTrunk) -> Dict[str, Any]:
        provider = get_carrier(record.carrier).credential_provider()
        if not provider:
            return {}
        return channel_config(provider, org_id=self.org_id, db=self.db)

    def _commit(self, conflict_detail: str) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail=conflict_detail) from exc

    def _get_record(self, trunk_id: Union[str, UUID]) -> SipTrunk:
        uid = coerce_uuid(trunk_id)
        if not uid:
            raise HTTPException(status_code=400, detail="trunk_id must be a valid UUID")
        record = self.query(SipTrunk).filter(SipTrunk.id == uid).first()
        if record is None:
            raise HTTPException(status_code=404, detail="SIP trunk not found")
        return record
    