from sqlalchemy import Column, BigInteger, String, Text, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import time

from core.database.base import Base
from core.models.enums import Role, InviteStatus


class OrganizationInvite(Base):
    __tablename__ = 'organization_invites'
    __table_args__ = (UniqueConstraint('email', name='invite_email_unique'),)

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
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
