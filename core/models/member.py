from sqlalchemy import Column, BigInteger, String, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from core.models.base import TimestampModel
from core.models.enums import Role


class Member(TimestampModel):
    __tablename__ = 'members'
    __table_args__ = (UniqueConstraint('user_id', name='member_user_unique'),)

    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(Enum(Role), default=Role.MEMBER)
    custom_permissions = Column(JSONB, default=[])
    status = Column(String, default='active')
    created_by = Column(BigInteger, ForeignKey('users.id'))
    joined_at = Column(BigInteger)
    last_activity_at = Column(BigInteger)

