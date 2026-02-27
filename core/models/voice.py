from sqlalchemy import Column, BigInteger, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.models.base import TimestampModel

class Voice(TimestampModel):
    __tablename__ = "voices"
    __table_args__ = (
    UniqueConstraint("service_provider_id", "voice_id"),
)

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    voice_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    language = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    accent = Column(String, nullable=True)
    description = Column(String, nullable=True)
    service_provider_id = Column(BigInteger, ForeignKey("service_providers.id"), nullable=False)
    # model_id = Column(BigInteger, ForeignKey("models.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    sample_url = Column(String, nullable=True)
