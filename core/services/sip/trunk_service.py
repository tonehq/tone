import secrets
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
from core.services.sip.base import (SipCarrierError, SipTerminationError,
                                    TerminationEndpoint)
from core.services.sip.livekit_termination import LiveKitTermination
from core.services.sip.registry import get_carrier, supported_carriers
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
    def __init__(self, db, user_id=None, org_id=None):
        super().__init__(db, user_id=user_id, org_id=org_id)
        self._termination_client: Optional[LiveKitTermination] = None

    def _termination(self) -> LiveKitTermination:
        if self._termination_client is None:
            self._termination_client = LiveKitTermination(
                channel_config("livekit", org_id=self.org_id, db=self.db)
            )
        return self._termination_client

    def termination_endpoint(self) -> TerminationEndpoint:
        host = (settings.SIP_TERMINATION_FQDN or "").strip() or self._termination().sip_host
        return TerminationEndpoint(host=host, port=settings.SIP_TERMINATION_PORT or 0)

    def list_trunks(self) -> List[Dict[str, Any]]:
        rows = self.query(SipTrunk).order_by(SipTrunk.updated_at.desc()).all()
        return [self._response(row) for row in rows]

    def get_trunk(
        self, trunk_id: Union[str, UUID], include_auth: bool = False
    ) -> Dict[str, Any]:
        return self._response(self._get_record(trunk_id), include_auth=include_auth)

    def _response(self, record: SipTrunk, include_auth: bool = False) -> Dict[str, Any]:
        host = self.termination_endpoint().host
        payload = {
            **record.to_dict(),
            "termination_host": host,
            "inbound_uri_template": f"sip:{{number}}@{host}" if host else "",
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

        try:
            self._termination().remove_trunk(record.carrier_config or {})
        except SipTerminationError:
            logger.exception("[sip] livekit trunk removal failed trunk={}", record.id)

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
            result = get_carrier(record.carrier).provision_trunk(
                record, credentials, self.termination_endpoint(),
                self.outbound_credentials(record),
            )
            record.carrier_config = {**(record.carrier_config or {}), **result.carrier_ids}
            termination_payload = self.termination_payload(record)
            livekit_ids = self._termination().sync_trunk(termination_payload)
            record.carrier_config = {**record.carrier_config, **livekit_ids}
            record.status = STATUS_PROVISIONED

            notes = [result.detail] if result.detail else []
            if not termination_payload["numbers"]:
                notes.append(
                    "Attach a phone number to this trunk to activate SIP routing — "
                    "LiveKit trunks are created once the trunk has at least one number."
                )
            record.status_detail = " | ".join(notes) or None
        except (SipCarrierError, SipTerminationError) as exc:
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
        moved_from = None
        if existing is not None and existing.channel_id != record.channel_id:
            previous = (
                self.db.query(Channel).filter(Channel.id == existing.channel_id).first()
            )
            moved_from = previous.name if previous is not None else str(existing.channel_id)

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
        else:
            existing.channel_id = record.channel_id
            if label:
                existing.label = label
        self.db.commit()
        self.db.refresh(existing)

        self._invalidate_number_cache(normalized)
        self._resync_termination(record)
        logger.info(
            "[sip] number attached trunk={} number={} moved_from={}",
            record.id, normalized, moved_from,
        )
        return {
            "id": str(existing.id),
            "number": existing.number,
            "label": existing.label,
            "channel_id": str(existing.channel_id),
            "sip_trunk_id": str(record.id),
            "agent_id": str(existing.agent_id) if existing.agent_id else None,
            "moved_from": moved_from,
        }

    @staticmethod
    def _invalidate_number_cache(number: str) -> None:
        from core.services.redis_service import cache_delete

        try:
            cache_delete(f"phone_to_agent:{number}")
        except Exception:
            logger.debug("[sip] phone_to_agent cache invalidation skipped for {}", number)

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
        self._resync_termination(record)
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

    def _resync_termination(self, record: SipTrunk) -> None:
        if record.status not in (STATUS_PROVISIONED, STATUS_ERROR):
            return
        try:
            livekit_ids = self._termination().sync_trunk(self.termination_payload(record))
        except SipTerminationError as exc:
            logger.exception("[sip] livekit resync failed trunk={}", record.id)
            record.status = STATUS_ERROR
            record.status_detail = str(exc)[:500]
            self.db.commit()
            return
        record.carrier_config = {**(record.carrier_config or {}), **livekit_ids}
        record.status = STATUS_PROVISIONED
        record.status_detail = None
        self.db.commit()

    def outbound_credentials(self, record: SipTrunk) -> Dict[str, str]:
        auth = trunk_auth(record)
        username = auth.get("auth_username") or auth.get("outbound_username") or ""
        password = auth.get("auth_password") or auth.get("outbound_password") or ""
        if username and password:
            return {"auth_username": username, "auth_password": password}

        username = f"tone{str(record.id).replace('-', '')[:12]}"
        password = secrets.token_urlsafe(21)
        record.encrypted_auth = encrypt_json(
            {**auth, "outbound_username": username, "outbound_password": password}
        )
        self.db.commit()
        logger.info("[sip] generated outbound credentials trunk={}", record.id)
        return {"auth_username": username, "auth_password": password}

    def termination_payload(self, record: SipTrunk) -> Dict[str, Any]:
        auth = trunk_auth(record)
        numbers = [
            row.number
            for row in self.query(PhoneNumber)
            .filter(PhoneNumber.channel_id == record.channel_id)
            .all()
        ]
        return {
            "trunk_id": str(record.id),
            "organization_id": str(record.organization_id),
            "name": record.name,
            "carrier": record.carrier,
            "numbers": numbers,
            "livekit_ids": record.carrier_config or {},
            "inbound": {
                "enabled": bool(record.inbound_enabled and record.is_active),
                "auth_mode": record.auth_mode,
                "auth_username": auth.get("auth_username") or "",
                "auth_password": auth.get("auth_password") or "",
                "allowed_hosts": validation.inbound_source_hosts(record.gateways),
            },
            "outbound": {
                "enabled": bool(record.outbound_enabled and record.is_active),
                "gateways": validation.outbound_gateways(record.gateways),
                **self.outbound_credentials(record),
            },
            "media_encryption": record.media_encryption,
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
    