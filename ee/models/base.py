from sqlalchemy import Column, BigInteger, ForeignKey
from core.database.base import Base

from core.context import get_current_org_id


class MultiTenantBase(Base):
    __abstract__ = True
    organization_id = Column(
        BigInteger,
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        default=get_current_org_id
    )
