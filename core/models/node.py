from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class Node(TimestampModel):
    __tablename__ = "nodes"

    name = Column(String(255), nullable=False, unique=True, index=True)
    environment = Column(String(50), nullable=True, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    pods = relationship("Pod", back_populates="node")
