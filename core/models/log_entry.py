from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class CallPipelineLog(OrgScopedModel):
    """All of one finished call's log lines, read back from Grafana Loki and
    stored as a single JSON array — ONE row per call.

    Replaces the earlier per-line ``pipeline_logs`` table: a call's lines now
    live in the ``logs`` JSONB array on a single row keyed by ``call_id``
    (UNIQUE), so the per-call viewer reads one row and a re-sync replaces the
    array wholesale. Populated by ``PipelineLogSyncService`` after a call ends
    (via the ``sync_loki_logs`` post-call action or the manual sync endpoint).
    Identity columns (``call_id``/``organization_id``/``agent_id``/``trace_id``)
    are STAMPED from the ``Call`` row — never parsed from the line text — so
    viewer queries stay tenant-scoped and reliable.

    Idempotency comes from the bounded per-call fetch window, not a per-line
    unique key: every sync re-reads the same window, rebuilds the same
    de-duplicated, time-ordered array, and upserts it
    (``on_conflict(call_id) do update``). So the post-call action, a manual
    re-sync, task retries and concurrent runs all converge on one row with the
    same contents. Each ``logs`` element is
    ``{ts, ts_ns, level, logger_name, message, raw_line}``; identity is not
    repeated per element (it lives on the row).
    """

    __tablename__ = "call_pipeline_logs"

    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        # UNIQUE — one row per call; its index also serves the viewer lookup.
        unique=True,
    )
    agent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    trace_id = Column(String(128), nullable=True, index=True)

    # Time-ordered (oldest first) array of the call's log lines. Each element is
    # {ts, ts_ns, level, logger_name, message, raw_line}.
    logs = Column(JSONB, nullable=False, default=list)
    # When ``logs`` was last (re)synced from Loki.
    synced_at = Column(DateTime(timezone=True), nullable=True)
