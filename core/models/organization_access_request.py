from sqlalchemy import Column, BigInteger, Text, Enum, ForeignKey, UniqueConstraint

from core.models.base import TimestampModel
from core.models.enums import AccessRequestStatus


class OrganizationAccessRequest(TimestampModel):
    __tablename__ = 'organization_access_requests'
    __table_args__ = (UniqueConstraint('user_id', name='org_access_request_unique'),)

    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING)
    message = Column(Text)
    reviewed_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(BigInteger)

