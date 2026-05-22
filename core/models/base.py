import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from core.database.base import Base
from core.context import get_current_org_id


class TimestampModel(Base):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SoftDeleteMixin:
    """Mixin for tables that support is_active + soft-delete/archive timestamps."""
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)


class OrgScopedModel(TimestampModel):
    """Base for org-scoped tables. organization_id is a plain UUID (not a FK)
    used for app-level filtering and future sharding."""
    __abstract__ = True

    organization_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        default=get_current_org_id,
    )
