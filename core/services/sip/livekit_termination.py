import asyncio
import ipaddress
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from livekit import api
from loguru import logger

from core.services.sip.base import SipTerminationError
from core.services.sip.validation import DEFAULT_SIP_PORT

SIP_ROOM_PREFIX = "sip-"
BOT_IDENTITY = "agent"
CALLER_IDENTITY_PREFIX = "caller-"


def livekit_sip_host(livekit_url: str) -> str:
    host = urlparse(livekit_url or "").hostname or (livekit_url or "").strip()
    if not host:
        return ""
    if host.endswith(".sip.livekit.cloud"):
        return host
    project, _, domain = host.partition(".")
    return f"{project}.sip.{domain}" if project and domain else ""


def ip_acl_entries(hosts: List[str]) -> List[str]:
    entries = []
    for host in hosts or []:
        try:
            entries.append(str(ipaddress.ip_network(host, strict=False)))
        except ValueError:
            logger.info(
                "[sip] livekit ip-acl skipping non-IP gateway host {} — LiveKit allows "
                "IP addresses and CIDR blocks only",
                host,
            )
    return entries


def _http_url(livekit_url: str) -> str:
    return (livekit_url or "").replace("wss://", "https://").replace("ws://", "http://")


class LiveKitTermination:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self._url = (config.get("url") or "").strip()
        self._api_key = (config.get("api_key") or "").strip()
        self._api_secret = (config.get("api_secret") or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self._url and self._api_key and self._api_secret)

    @property
    def sip_host(self) -> str:
        return livekit_sip_host(self._url)

    def _require_configured(self) -> None:
        if not self.configured:
            raise SipTerminationError(
                "No LiveKit channel configured for this organization. Add a LiveKit "
                "channel with url + api_key + api_secret before provisioning a SIP trunk."
            )

    def _run(self, factory):
        self._require_configured()

        async def _call():
            client = api.LiveKitAPI(_http_url(self._url), self._api_key, self._api_secret)
            try:
                return await factory(client)
            finally:
                await client.aclose()

        try:
            return asyncio.run(_call())
        except SipTerminationError:
            raise
        except Exception as exc:
            logger.exception("[sip] livekit api call failed")
            raise SipTerminationError(f"LiveKit SIP API error: {exc}")

    def sync_trunk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        inbound = payload.get("inbound") or {}
        outbound = payload.get("outbound") or {}
        existing = payload.get("livekit_ids") or {}
        name = payload.get("name") or payload["trunk_id"]
        numbers: List[str] = payload.get("numbers") or []

        async def _sync(client):
            ids: Dict[str, Any] = {
                "inbound_trunk_id": "",
                "outbound_trunk_id": "",
                "dispatch_rule_id": "",
            }

            await self._purge_existing(client, payload["trunk_id"], name, existing)

            if not numbers:
                logger.info(
                    "[sip] livekit trunk sync skipped trunk={} — no numbers attached yet",
                    payload.get("trunk_id"),
                )
                return ids

            if inbound.get("enabled"):
                trunk = api.SIPInboundTrunkInfo(
                    name=name,
                    metadata=payload["trunk_id"],
                    numbers=numbers,
                    krisp_enabled=True,
                )
                if inbound.get("auth_mode") == "digest":
                    trunk.auth_username = inbound.get("auth_username") or ""
                    trunk.auth_password = inbound.get("auth_password") or ""
                else:
                    trunk.allowed_addresses.extend(
                        ip_acl_entries(inbound.get("allowed_hosts") or [])
                    )
                created = await client.sip.create_sip_inbound_trunk(
                    api.CreateSIPInboundTrunkRequest(trunk=trunk)
                )
                ids["inbound_trunk_id"] = created.sip_trunk_id

                rule = await client.sip.create_sip_dispatch_rule(
                    api.CreateSIPDispatchRuleRequest(
                        name=name,
                        metadata=payload["trunk_id"],
                        trunk_ids=[created.sip_trunk_id],
                        rule=api.SIPDispatchRule(
                            dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                                room_prefix=SIP_ROOM_PREFIX
                            )
                        ),
                    )
                )
                ids["dispatch_rule_id"] = rule.sip_dispatch_rule_id

            if outbound.get("enabled") and outbound.get("gateways"):
                gateway = outbound["gateways"][0]
                trunk = api.SIPOutboundTrunkInfo(
                    name=name,
                    metadata=payload["trunk_id"],
                    address=gateway["host"],
                    transport=self._transport(gateway.get("transport")),
                    numbers=numbers,
                )
                if outbound.get("auth_username"):
                    trunk.auth_username = outbound["auth_username"]
                    trunk.auth_password = outbound.get("auth_password") or ""
                created = await client.sip.create_sip_outbound_trunk(
                    api.CreateSIPOutboundTrunkRequest(trunk=trunk)
                )
                ids["outbound_trunk_id"] = created.sip_trunk_id

            return ids

        ids = self._run(_sync)
        logger.info("[sip] livekit trunk synced trunk={} ids={}", payload.get("trunk_id"), ids)
        return ids

    @staticmethod
    async def _purge_existing(
        client, trunk_id: str, name: str, existing: Dict[str, Any]
    ) -> None:
        def owned(item) -> bool:
            return getattr(item, "metadata", "") == trunk_id or getattr(item, "name", "") == name

        try:
            rules = await client.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())
            for rule in rules.items:
                if owned(rule) or rule.sip_dispatch_rule_id == existing.get("dispatch_rule_id"):
                    await client.sip.delete_sip_dispatch_rule(
                        api.DeleteSIPDispatchRuleRequest(
                            sip_dispatch_rule_id=rule.sip_dispatch_rule_id
                        )
                    )
                    logger.info("[sip] livekit removed dispatch rule {}", rule.sip_dispatch_rule_id)
        except Exception as exc:
            logger.debug("[sip] livekit dispatch rule cleanup skipped: {}", exc)

        tracked = {existing.get("inbound_trunk_id"), existing.get("outbound_trunk_id")}
        for lister, request in (
            (client.sip.list_sip_inbound_trunk, api.ListSIPInboundTrunkRequest()),
            (client.sip.list_sip_outbound_trunk, api.ListSIPOutboundTrunkRequest()),
        ):
            try:
                found = await lister(request)
                for item in found.items:
                    if owned(item) or item.sip_trunk_id in tracked:
                        await client.sip.delete_sip_trunk(
                            api.DeleteSIPTrunkRequest(sip_trunk_id=item.sip_trunk_id)
                        )
                        logger.info("[sip] livekit removed trunk {}", item.sip_trunk_id)
            except Exception as exc:
                logger.debug("[sip] livekit trunk cleanup skipped: {}", exc)

    @staticmethod
    def _transport(transport: Optional[str]):
        mapping = {
            "udp": api.SIPTransport.SIP_TRANSPORT_UDP,
            "tcp": api.SIPTransport.SIP_TRANSPORT_TCP,
            "tls": api.SIPTransport.SIP_TRANSPORT_TLS,
        }
        return mapping.get((transport or "udp").lower(), api.SIPTransport.SIP_TRANSPORT_UDP)

    def remove_trunk(self, livekit_ids: Dict[str, Any]) -> None:
        async def _remove(client):
            if livekit_ids.get("dispatch_rule_id"):
                await client.sip.delete_sip_dispatch_rule(
                    api.DeleteSIPDispatchRuleRequest(
                        sip_dispatch_rule_id=livekit_ids["dispatch_rule_id"]
                    )
                )
            for key in ("inbound_trunk_id", "outbound_trunk_id"):
                if livekit_ids.get(key):
                    await client.sip.delete_sip_trunk(
                        api.DeleteSIPTrunkRequest(sip_trunk_id=livekit_ids[key])
                    )

        self._run(_remove)

    def originate(
        self,
        outbound_trunk_id: str,
        to_number: str,
        from_number: str,
        room_name: str,
        attributes: Dict[str, str],
        ringing_timeout: int = 45,
    ) -> Dict[str, Any]:
        async def _dial(client):
            request = api.CreateSIPParticipantRequest(
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=to_number,
                sip_number=from_number,
                room_name=room_name,
                participant_identity=f"{CALLER_IDENTITY_PREFIX}{to_number}",
                participant_name=to_number,
                wait_until_answered=False,
                play_ringtone=True,
            )
            request.participant_attributes.update({k: str(v) for k, v in attributes.items()})
            request.ringing_timeout.FromSeconds(ringing_timeout)
            return await client.sip.create_sip_participant(request)

        info = self._run(_dial)
        return {
            "call_id": getattr(info, "sip_call_id", "") or getattr(info, "participant_id", ""),
            "participant_identity": getattr(info, "participant_identity", ""),
            "room_name": room_name,
            "status": "ringing",
        }

    def hangup(self, room_name: str, participant_identity: str) -> None:
        async def _hangup(client):
            await client.room.remove_participant(
                api.RoomParticipantIdentity(room=room_name, identity=participant_identity)
            )

        self._run(_hangup)

    def transfer(
        self,
        room_name: str,
        participant_identity: str,
        sip_address: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        async def _transfer(client):
            request = api.TransferSIPParticipantRequest(
                participant_identity=participant_identity,
                room_name=room_name,
                transfer_to=sip_address,
                play_dialtone=True,
            )
            if headers:
                request.headers.update(headers)
            await client.sip.transfer_sip_participant(request)

        self._run(_transfer)

    def bot_grant(self, room_name: str) -> Dict[str, str]:
        self._require_configured()
        from datetime import timedelta

        token = (
            api.AccessToken(self._api_key, self._api_secret)
            .with_identity(BOT_IDENTITY)
            .with_name(BOT_IDENTITY)
            .with_ttl(timedelta(hours=6))
            .with_grants(
                api.VideoGrants(
                    room_join=True, room=room_name, can_publish=True, can_subscribe=True
                )
            )
            .to_jwt()
        )
        return {"url": self._url, "token": token, "room": room_name}
