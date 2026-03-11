from sqlalchemy import Column, BigInteger, Text, Enum, ForeignKey, UniqueConstraint

from core.models.base import OrgScopedModel
from core.models.enums import AccessRequestStatus


class OrganizationAccessRequest(OrgScopedModel):
    __tablename__ = 'organization_access_requests'
    __table_args__ = (UniqueConstraint('organization_id', 'user_id', name='org_access_request_org_user_unique'),)

    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING)
    message = Column(Text)
    reviewed_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(BigInteger)

