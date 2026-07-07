from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class Pod(TimestampModel):
    __tablename__ = "pods"

    name = Column(String(255), nullable=False, unique=True, index=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    ordinal = Column(Integer, nullable=True)
    environment = Column(String(50), nullable=True, index=True)
    mem_used_mb = Column(Float, nullable=True)
    mem_limit_mb = Column(Float, nullable=True)
    cpu_used_cores = Column(Float, nullable=True)
    cpu_limit_cores = Column(Float, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    node = relationship("Node", back_populates="pods")
    calls = relationship("Call", back_populates="pod")
