from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from core.database.base import Base
from core.context import get_current_org_id
import time


class TimestampModel(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))


class OrgScopedModel(TimestampModel):
    __abstract__ = True

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        default=get_current_org_id
    )

