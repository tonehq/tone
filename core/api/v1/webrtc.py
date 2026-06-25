from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.models.agent import Agent
from core.models.agent_channel import AgentChannel
from core.models.channel import Channel
from core.services.webrtc import webrtc_session_service
from core.utils.encryption import decrypt_json
from shared.config import settings

router = APIRouter()


class StartAgentRequest(BaseModel):
    channel_id: Optional[str] = None


@router.post("/agent/{agent_id}/start")
async def start_agent(
    agent_id: UUID,
    body: StartAgentRequest = Body(default=StartAgentRequest()),
    db: Session = Depends(get_db),
    claims: JWTClaims = Depends(require_org_member),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.organization_id == org_id, Agent.deleted_at.is_(None))
        .first()
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    query = (
        db.query(Channel)
        .join(AgentChannel, AgentChannel.channel_id == Channel.id)
        .filter(AgentChannel.agent_id == agent.id, AgentChannel.organization_id == org_id)
    )
    if body.channel_id:
        query = query.filter(Channel.id == UUID(body.channel_id))
    channels = query.all()
    if not channels:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No web channel enabled for this agent",
        )
    if len(channels) > 1 and not body.channel_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple web channels enabled — pass channel_id",
        )

    channel = channels[0]
    if not channel.encrypted_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="This channel is not configured",
        )

    config = decrypt_json(channel.encrypted_config)
    try:
        session = await webrtc_session_service().start(agent, channel.channel_type, config)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return {
        "provider": session.provider,
        "room": session.room,
        "room_url": session.client_url,
        "url": session.url,
        "token": session.token,
    }
