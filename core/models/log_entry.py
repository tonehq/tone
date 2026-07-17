from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class PipelineLog(OrgScopedModel):
    """One log line of a single finished call, read back from Grafana Loki.

    Populated by ``PipelineLogSyncService`` after a call ends (via the
    ``sync_loki_logs`` post-call action or the manual sync endpoint) to power an
    in-product per-call log viewer. Identity columns (``call_id``,
    ``organization_id``, ``agent_id``, ``trace_id``) are STAMPED from the ``Call``
    row — never parsed from the line text — so viewer queries stay tenant-scoped
    and reliable. Only ``level``/``logger_name``/``message`` are parsed from the
    raw line, defensively (``raw_line`` always preserves the original).

    ``fingerprint`` (sha256 of ts + labels + line) is UNIQUE so re-runs of the
    same call — the post-call action and a manual re-sync, task retries,
    concurrent runs — are idempotent via ``on_conflict_do_nothing``.
    """

    __tablename__ = "pipeline_logs"

    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    trace_id = Column(String(128), nullable=True, index=True)

    # Loki line timestamp. ``ts`` is tz-aware for range queries; ``ts_ns`` keeps
    # the original nanosecond precision Loki reports (and drives pagination).
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    ts_ns = Column(BigInteger, nullable=False)

    # Parsed defensively from the line — any may be NULL on a non-matching or
    # multiline line, in which case ``message`` falls back to the whole line.
    level = Column(String(16), nullable=True)
    logger_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)

    # The original Loki line, always stored verbatim (never dropped).
    raw_line = Column(Text, nullable=False)
    # Loki stream labels for the line (app, namespace, pod, …).
    labels = Column(JSONB, nullable=True)

    # sha256(ts_ns + sorted labels + raw line). Deterministic → dedup key.
    fingerprint = Column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_pipeline_logs_fingerprint"),
        # Primary viewer access path: a call's lines in time order.
        Index("ix_pipeline_logs_call_ts", "call_id", "ts"),
    )
