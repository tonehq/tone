from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

ProcrastinateBase = declarative_base()


class ProcrastinateWorker(ProcrastinateBase):
    __tablename__ = "procrastinate_workers"

    id = Column(BigInteger, primary_key=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=False)


class ProcrastinateJob(ProcrastinateBase):
    __tablename__ = "procrastinate_jobs"

    id = Column(BigInteger, primary_key=True)
    queue_name = Column(String(128), nullable=False)
    task_name = Column(String(128), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    lock = Column(Text, nullable=True)
    queueing_lock = Column(Text, nullable=True)
    args = Column(JSONB, nullable=False, default=dict)
    status = Column(String, nullable=False, default="todo")
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    abort_requested = Column(Boolean, nullable=False, default=False)
    worker_id = Column(
        BigInteger,
        ForeignKey("procrastinate_workers.id", ondelete="SET NULL"),
        nullable=True,
    )

    worker = relationship("ProcrastinateWorker", lazy="selectin")
    events = relationship(
        "ProcrastinateEvent",
        back_populates="job",
        lazy="selectin",
        order_by="ProcrastinateEvent.at",
    )

    @property
    def is_running(self) -> bool:
        return self.status == "doing"

    @property
    def is_finished(self) -> bool:
        return self.status in ("succeeded", "failed", "cancelled", "aborted")


class ProcrastinatePeriodicDefer(ProcrastinateBase):
    __tablename__ = "procrastinate_periodic_defers"

    id = Column(BigInteger, primary_key=True)
    task_name = Column(String(128), nullable=False)
    defer_timestamp = Column(BigInteger, nullable=True)
    job_id = Column(BigInteger, ForeignKey("procrastinate_jobs.id"), nullable=True)
    periodic_id = Column(String(128), nullable=False, default="")


class ProcrastinateEvent(ProcrastinateBase):
    __tablename__ = "procrastinate_events"

    id = Column(BigInteger, primary_key=True)
    job_id = Column(
        BigInteger,
        ForeignKey("procrastinate_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(String, nullable=True)
    at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("ProcrastinateJob", back_populates="events")
