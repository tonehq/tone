from sqlalchemy import Column, BigInteger, String, Text, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import time

from ee.database.base import EEBase
from core.models.enums import Role, InviteStatus


class OrganizationInvite(EEBase):
    __tablename__ = 'organization_invites'
    __table_args__ = (
        UniqueConstraint('email', 'organization_id', name='org_invite_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String)
    role = Column(Enum(Role), default=Role.MEMBER)
    status = Column(Enum(InviteStatus), default=InviteStatus.PENDING)
    invitation_token = Column(String, nullable=False, unique=True)
    expires_at = Column(BigInteger, nullable=False)
    invited_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    accepted_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    accepted_at = Column(BigInteger)
    message = Column(Text)
    custom_permissions = Column(JSONB, default=[])
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
