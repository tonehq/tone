from typing import Any, Dict, Optional
from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.channel import Channel
from core.utils.encryption import decrypt_json


def _decrypt_channel_config(channel: Optional[Channel]) -> Dict[str, Any]:
    if channel is None or not channel.encrypted_config:
        return {}
    try:
        return decrypt_json(channel.encrypted_config) or {}
    except Exception as exc:
        logger.warning(f"[call_engines.credentials] decrypt failed for channel {channel.id}: {exc}")
        return {}


def fetch_channel_credentials(
    provider_slug: str,
    org_id: Optional[UUID] = None,
    channel_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    with get_db_context() as db:
        if channel_id:
            channel = db.query(Channel).filter(Channel.id == channel_id).first()
            config = _decrypt_channel_config(channel)
            if config:
                return config

        query = db.query(Channel).filter(Channel.channel_type == provider_slug)
        if org_id:
            query = query.filter(Channel.organization_id == org_id)

        channel = query.first()
        config = _decrypt_channel_config(channel)
        if not config:
            logger.warning(
                f"[call_engines.credentials] no {provider_slug} channel found "
                f"(org_id={org_id}, channel_id={channel_id})"
            )
        return config
