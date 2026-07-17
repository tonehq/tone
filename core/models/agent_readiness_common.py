"""Shared column set for the two readiness tables.

Both ``AgentReadinessSnapshot`` (latest state) and ``AgentReadinessEvent``
(append-only history) carry identical columns — the only difference is the
uniqueness constraint. Defining the columns once here means schema changes
propagate to both tables automatically and the two can never drift.

Mirrors the ``SoftDeleteMixin`` pattern already used in ``core/models/base.py``
— plain ``Column`` definitions inside a mixin class; SQLAlchemy handles the
per-subclass instantiation.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID


class ReadinessRowMixin:
    """Every column that describes one readiness run.

    Columns are grouped by intent:
    - Identity: which agent + config + depth this row is about
    - Report summary: overall_status + per-severity counts + full check list
    - Provenance: how the run was triggered, by whom, how long it took, and
      the version stamp that governs edit-based freshness
    """

    # ── Identity ──────────────────────────────────────────────────────────
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: the "brand-new agent with no config yet" case still deserves
    # a row so the sidebar can show an onboarding-style checklist.
    config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_configs.id", ondelete="CASCADE"),
        nullable=True,
    )
    depth = Column(String(16), nullable=False)  # "shallow" | "deep"

    # ── Report summary (the render-ready payload) ─────────────────────────
    overall_status = Column(String(24), nullable=False)  # ready | ready_with_warnings | not_ready
    # All per-severity/status tallies in one JSONB blob — mirrors the API's
    # `summary` field exactly (blockers, warnings, info, passed, skipped).
    # Storing them together means we can add a new severity later without a
    # migration and keeps the row shape aligned with what callers already read.
    counts = Column(JSONB, nullable=False, default=dict)
    # Full flat list of CheckResult dicts — same shape as the API response, so
    # reading a stored row is a zero-work render.
    checks = Column(JSONB, nullable=False, default=list)

    # ── Provenance ────────────────────────────────────────────────────────
    # Why this run happened. Free-form string but callers should pick from
    # the set the schemas enum documents (editor_load, publish_gate, etc.)
    # so downstream analytics stay comparable.
    trigger = Column(String(32), nullable=False)
    triggered_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    duration_ms = Column(Integer, nullable=True)
    # Wall-clock start of the run. Together with ``computed_at`` (end) this
    # gives the drawer a "started at → finished at" pair without deriving one
    # from the other via ``duration_ms``.
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # Per-agent run counter, monotonically increasing across all configs and
    # depths. Snapshot rows always carry the *latest* run number (row is
    # UPSERTed); event rows form the full 1..N sequence. UI can read
    # snapshot.run_number for a "Run #10" badge without a subquery.
    run_number = Column(Integer, nullable=False, default=1)
    # Optional human-readable label for the run. Nullable; no writers yet.
    name = Column(String(255), nullable=True)
    # The freshness key. Reused from `compute_agent_cache_version` in the
    # pipeline resolver — a snapshot with a matching stamp is definitionally
    # still valid (nothing the check depends on has changed).
    dependency_stamp = Column(Text, nullable=False)
    # Populated only if the runner itself crashed (rare — checks catch their
    # own failures). Kept nullable so happy-path rows stay compact.
    error = Column(Text, nullable=True)
