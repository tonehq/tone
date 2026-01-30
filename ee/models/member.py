from sqlalchemy import Column, BigInteger, String, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import time

from ee.database.base import EEBase
from core.models.enums import Role


class Member(EEBase):
    __tablename__ = 'members'
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='org_member_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(Enum(Role), default=Role.MEMBER)
    custom_permissions = Column(JSONB, default=[])
    status = Column(String, default='active')
    created_by = Column(BigInteger, ForeignKey('users.id'))
    joined_at = Column(BigInteger)
    last_activity_at = Column(BigInteger)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
