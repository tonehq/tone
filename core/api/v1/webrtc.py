from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.models.agent import Agent
from core.models.agent_channel import AgentChannel
from core.models.channel import Channel
from core.services.webrtc import webrtc_session_service
from core.utils.encryption import decrypt_json

router = APIRouter()


@router.post("/call/{slug}")
async def start_web_call(slug: str, db: Session = Depends(get_db)):
    binding = db.query(AgentChannel).filter(AgentChannel.slug == slug).first()
    if binding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call link not found")

    agent = (
        db.query(Agent)
        .filter(Agent.id == binding.agent_id, Agent.deleted_at.is_(None))
        .first()
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    channel = db.query(Channel).filter(Channel.id == binding.channel_id).first()
    if channel is None or not channel.encrypted_config:
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
        "url": session.url,
        "token": session.token,
        "client_url": session.client_url,
    }
