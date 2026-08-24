from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from core.models.sip_trunk import SipTrunk
from core.services.agent_runner_service import AgentRunnerService
from core.services.sip.trunk_service import trunk_auth
from core.services.sip.validation import (DEFAULT_SIP_SAMPLE_RATE,
                                          host_matches_source,
                                          inbound_source_hosts)


def trunk_by_id(db: Session, trunk_id: str) -> Optional[SipTrunk]:
    if not trunk_id:
        return None
    return db.query(SipTrunk).filter(SipTrunk.id == trunk_id).first()


def trunk_by_auth_username(db: Session, username: str) -> Optional[SipTrunk]:
    if not username:
        return None
    return (
        db.query(SipTrunk)
        .filter(
            SipTrunk.auth_username == username.strip(),
            SipTrunk.auth_mode == "digest",
            SipTrunk.is_active.is_(True),
        )
        .first()
    )


def trunk_by_source_ip(db: Session, source_ip: str) -> Optional[SipTrunk]:
    if not source_ip:
        return None
    candidates: List[SipTrunk] = (
        db.query(SipTrunk)
        .filter(
            SipTrunk.auth_mode == "ip_acl",
            SipTrunk.is_active.is_(True),
            SipTrunk.inbound_enabled.is_(True),
        )
        .all()
    )
    for trunk in candidates:
        hosts = inbound_source_hosts(trunk.gateways)
        if any(host_matches_source(host, source_ip) for host in hosts):
            return trunk
    return None


def resolve_trunk(
    db: Session,
    trunk_id: Optional[str] = None,
    auth_username: Optional[str] = None,
    source_ip: Optional[str] = None,
) -> Optional[SipTrunk]:
    return (
        trunk_by_id(db, trunk_id or "")
        or trunk_by_auth_username(db, auth_username or "")
        or trunk_by_source_ip(db, source_ip or "")
    )


def digest_credentials(db: Session, auth_username: str) -> Dict[str, Any]:
    trunk = trunk_by_auth_username(db, auth_username)
    if trunk is None:
        return {}
    auth = trunk_auth(trunk)
    if not auth.get("auth_password"):
        return {}
    return {
        "trunk_id": str(trunk.id),
        "auth_username": auth.get("auth_username"),
        "auth_password": auth.get("auth_password"),
    }


def resolve_inbound_call(
    db: Session,
    to_number: str,
    source_ip: Optional[str] = None,
    auth_username: Optional[str] = None,
    trunk_id: Optional[str] = None,
    media_ws_url: str = "",
) -> Dict[str, Any]:
    trunk = resolve_trunk(db, trunk_id, auth_username, source_ip)
    if trunk is None:
        logger.warning(
            "[sip] inbound rejected — no trunk matched source_ip={} username={} trunk_id={}",
            source_ip, auth_username, trunk_id,
        )
        return {"allowed": False, "reason": "no_matching_trunk"}

    if not trunk.is_active or not trunk.inbound_enabled:
        logger.warning("[sip] inbound rejected — trunk {} is not accepting inbound", trunk.id)
        return {"allowed": False, "reason": "inbound_disabled", "trunk_id": str(trunk.id)}

    agent = AgentRunnerService(db, org_id=trunk.organization_id).get_agent_by_phone_number(
        to_number
    )
    if agent is None:
        logger.warning(
            "[sip] inbound rejected — no agent assigned to {} on trunk {}", to_number, trunk.id
        )
        return {"allowed": False, "reason": "no_agent_for_number", "trunk_id": str(trunk.id)}

    logger.info(
        "[sip] inbound routed trunk={} to={} agent={} ws_url={}",
        trunk.id, to_number, agent.id, media_ws_url,
    )
    return {
        "allowed": True,
        "trunk_id": str(trunk.id),
        "organization_id": str(trunk.organization_id),
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "media_ws_url": media_ws_url,
        "media_encryption": trunk.media_encryption,
        "sample_rate": DEFAULT_SIP_SAMPLE_RATE,
        "transfer_enabled": bool(trunk.transfer_enabled),
    }
