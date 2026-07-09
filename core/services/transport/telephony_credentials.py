"""Telephony provider credentials.

Channels store credentials in ``encrypted_config`` keyed by ``channel_type``
("twilio"/"telnyx"/"plivo"/"exotel"). These helpers decrypt that config so the
per-provider call engines can build their frame serializers.
"""

from loguru import logger


def channel_config(provider_slug: str, org_id=None, channel_id=None, db=None) -> dict:
    """Decrypt a telephony Channel's config.

    Channels store credentials in `encrypted_config` keyed by `channel_type`
    ("twilio"/"telnyx"/"plivo"/"exotel"). Prefers a specific `channel_id` when given,
    else the org-scoped channel of that type. Pass an existing `db` session to reuse it;
    otherwise a short-lived session is opened. Returns the decrypted dict or {}.

    Single source of truth for telephony channel decryption — used by the transport
    serializers, AgentRunnerService, and the pipeline service_resolver.
    """
    from core.models.channel import Channel
    from core.utils.encryption import decrypt_json

    def _decrypt(channel) -> dict:
        if not channel or not channel.encrypted_config:
            return {}
        try:
            return decrypt_json(channel.encrypted_config) or {}
        except Exception as e:
            logger.warning("Failed to decrypt %s channel config: %s", provider_slug, e)
            return {}

    def _query(session) -> dict:
        if channel_id:
            cfg = _decrypt(session.query(Channel).filter(Channel.id == channel_id).first())
            if cfg:
                return cfg
        q = session.query(Channel).filter(Channel.channel_type == provider_slug)
        if org_id:
            q = q.filter(Channel.organization_id == org_id)
        return _decrypt(q.first())

    if db is not None:
        return _query(db)
    from core.database.session import get_db_context

    with get_db_context() as session:
        return _query(session)


def get_twilio_credentials(org_id=None, channel_id=None) -> dict:
    """Fetch Twilio account_sid and auth_token. When ``channel_id`` is given,
    the credentials come from that specific channel (correct when an org has
    multiple Twilio accounts); otherwise falls back to the org's first Twilio channel."""
    cfg = channel_config("twilio", org_id, channel_id=channel_id)
    account_sid = cfg.get("account_sid")
    auth_token = cfg.get("auth_token")
    if account_sid and auth_token:
        return {"account_sid": account_sid, "auth_token": auth_token}
    return {}


def get_plivo_credentials(org_id=None, channel_id=None) -> dict:
    """Fetch Plivo auth_id and auth_token. When ``channel_id`` is given, the
    credentials come from that specific channel (correct when an org has multiple
    Plivo accounts); otherwise falls back to the org's first Plivo channel."""
    cfg = channel_config("plivo", org_id, channel_id=channel_id)
    auth_id = cfg.get("auth_id")
    auth_token = cfg.get("auth_token")
    if auth_id and auth_token:
        return {"auth_id": auth_id, "auth_token": auth_token}
    return {}


def get_telnyx_api_key(org_id=None, channel_id=None) -> str:
    """Fetch the Telnyx API key. When ``channel_id`` is given, the key comes from
    that specific channel (correct when an org has multiple Telnyx accounts);
    otherwise falls back to the org's first Telnyx channel."""
    return channel_config("telnyx", org_id, channel_id=channel_id).get("api_key") or ""


def get_exotel_credentials(org_id=None, channel_id=None) -> dict:
    """Fetch Exotel api_key, api_token, account_sid, subdomain. When ``channel_id``
    is given, the credentials come from that specific channel (correct when an org
    has multiple Exotel accounts); otherwise falls back to the org's first Exotel channel."""
    cfg = channel_config("exotel", org_id, channel_id=channel_id)
    api_key = cfg.get("api_key")
    api_token = cfg.get("api_token")
    account_sid = cfg.get("account_sid")
    subdomain = cfg.get("subdomain")
    if api_key and api_token and account_sid:
        return {
            "api_key": api_key,
            "api_token": api_token,
            "account_sid": account_sid,
            "subdomain": subdomain or "api.exotel.com",
        }
    return {}
