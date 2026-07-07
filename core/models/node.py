from sqlalchemy import Column, String, DateTime, Integer, Float
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class Node(TimestampModel):
    __tablename__ = "nodes"

    name = Column(String(255), nullable=False, unique=True, index=True)
    environment = Column(String(50), nullable=True, index=True)
    total_vcpu = Column(Float, nullable=True)
    total_ram_mb = Column(Integer, nullable=True)
    vcpu_per_pod = Column(Float, nullable=True)
    ram_per_pod_mb = Column(Float, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    pods = relationship("Pod", back_populates="node")
