from sqlalchemy import Column, BigInteger, Text, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import time

from ee.database.base import EEBase
from core.models.enums import AccessRequestStatus


class OrganizationAccessRequest(EEBase):
    __tablename__ = 'organization_access_requests'
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='org_access_request_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    status = Column(Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING)
    message = Column(Text)
    reviewed_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(BigInteger)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
