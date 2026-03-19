import uuid

from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class Upload(OrgScopedModel):
    __tablename__ = 'uploads'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    r2_object_key = Column(String, nullable=False)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=False, index=True)
    call_log_id = Column(BigInteger, ForeignKey('call_logs.id'), nullable=True, index=True)
    file_name = Column(String, nullable=True)
    content_type = Column(String, nullable=True, default='audio/mpeg')
    file_size_bytes = Column(BigInteger, nullable=True)
