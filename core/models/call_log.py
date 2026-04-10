import uuid

from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class CallLog(OrgScopedModel):
    __tablename__ = 'call_logs'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=False, index=True)
    provider_call_id = Column(String, nullable=True)
    transport_type = Column(String, nullable=True)
    from_number = Column(String, nullable=True)
    to_number = Column(String, nullable=True)
    audio_file_path = Column(String, nullable=True)
    upload_id = Column(BigInteger, ForeignKey('uploads.id'), nullable=True, index=True)
    transcript = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, default='in_progress')
    started_at = Column(BigInteger, nullable=False)
    ended_at = Column(BigInteger, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    metrics = Column(JSONB, nullable=True)
