from sqlalchemy import Column, BigInteger, String, Text, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import time

from ee.database.base import EEBase
from core.models.enums import OrganizationStatus


class Organization(EEBase):
    __tablename__ = 'organizations'
    __table_args__ = (
        UniqueConstraint('slug', name='org_slug_unique'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    description = Column(Text)
    logo_url = Column(String)
    website_url = Column(String)
    settings = Column(JSONB, default={})
    status = Column(Enum(OrganizationStatus), default=OrganizationStatus.ACTIVE)
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    subscription_plan = Column(String, default='free')
    subscription_status = Column(String, default='active')
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
