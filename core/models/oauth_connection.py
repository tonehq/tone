import uuid

from sqlalchemy import Column, BigInteger, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class OAuthConnection(OrgScopedModel):
    __tablename__ = 'oauth_connections'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)  # NULL = org-level, set = user-level
    provider = Column(String, nullable=False)  # e.g. "google_calendar", "google_sheets", "hubspot"
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(BigInteger, nullable=True)
    scopes = Column(String, nullable=True)
    user_email = Column(String, nullable=True)  # the connected account's email
    is_active = Column(Boolean, default=True, nullable=False)
    meta_data = Column(JSONB, nullable=True, default=dict)  # provider-specific config
