"""add run_number + started_at to agent_readiness_snapshots + agent_readiness_events

Both readiness tables share ``ReadinessRowMixin`` (see
``core/models/agent_readiness_common.py``) so the same two columns land on both:

* ``run_number`` — per-agent monotonically increasing counter (1, 2, 3, …).
  Snapshot row (UPSERTed on agent+config+depth) always carries the latest count;
  event rows form the full sequence.
* ``started_at`` — wall-clock start of the run. Together with the existing
  ``computed_at`` (end) this gives the drawer a "started → finished" pair
  without deriving one via ``duration_ms``.

Backfill strategy:
* ``run_number`` — assign ``row_number() OVER (PARTITION BY agent_id ORDER BY
  computed_at ASC)`` on the event table, then set each snapshot's ``run_number``
  to the corresponding event row's count (the latest run for that
  agent+config+depth combo).
* ``started_at`` — ``computed_at - COALESCE(duration_ms, 0)`` on both tables.
  Existing rows lose no data (both columns are already present) and the derived
  ``started_at`` is a reasonable approximation until the next run fills in the
  exact wall-clock value.

Revision ID: a7e12c9f4b5d
Revises: d4b2f8a1c6e3
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa


revision = "a7e12c9f4b5d"
down_revision = "d4b2f8a1c6e3"
branch_labels = None
depends_on = None


_TABLES = ("agent_readiness_snapshots", "agent_readiness_events")


def upgrade() -> None:
    # Add both columns nullable first so backfill can populate them, then
    # tighten to NOT NULL. Same pattern the codebase uses elsewhere for
    # non-nullable adds against non-empty tables.
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("run_number", sa.Integer(), nullable=True),
        )

    # ── Backfill started_at on both tables ────────────────────────────────
    # computed_at - duration_ms (fall back to 0ms when duration is null).
    op.execute(
        """
        UPDATE agent_readiness_snapshots
        SET started_at = computed_at
                         - (COALESCE(duration_ms, 0) || ' milliseconds')::interval
        WHERE started_at IS NULL
        """
    )
    op.execute(
        """
        UPDATE agent_readiness_events
        SET started_at = computed_at
                         - (COALESCE(duration_ms, 0) || ' milliseconds')::interval
        WHERE started_at IS NULL
        """
    )

    # ── Backfill run_number on the event table (source of truth) ──────────
    # Sequence per agent by chronological computed_at. Ties broken by id so
    # the assignment is deterministic across re-runs.
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY agent_id
                       ORDER BY computed_at ASC, id ASC
                   ) AS rn
            FROM agent_readiness_events
        )
        UPDATE agent_readiness_events e
        SET run_number = numbered.rn
        FROM numbered
        WHERE e.id = numbered.id
          AND e.run_number IS NULL
        """
    )

    # Snapshot's run_number = the LATEST run_number for that
    # (agent_id, config_id, depth) triple, sourced from the event log.
    # NULL-safe comparison on config_id because a brand-new agent's snapshot
    # can have config_id NULL and the event row will too.
    op.execute(
        """
        UPDATE agent_readiness_snapshots s
        SET run_number = latest.max_rn
        FROM (
            SELECT agent_id,
                   config_id,
                   depth,
                   MAX(run_number) AS max_rn
            FROM agent_readiness_events
            GROUP BY agent_id, config_id, depth
        ) AS latest
        WHERE s.agent_id = latest.agent_id
          AND s.depth    = latest.depth
          AND s.config_id IS NOT DISTINCT FROM latest.config_id
          AND s.run_number IS NULL
        """
    )
    # Any snapshot without a matching event (edge case — event write failed
    # historically) starts at 1 so the NOT NULL constraint below holds.
    op.execute(
        """
        UPDATE agent_readiness_snapshots
        SET run_number = 1
        WHERE run_number IS NULL
        """
    )

    # ── Tighten to NOT NULL now that both columns are populated ──────────
    for table in _TABLES:
        op.alter_column(table, "started_at", nullable=False)
        op.alter_column(table, "run_number", nullable=False)

    # Fast "latest N runs for one agent, ordered by run_number" reads. Pairs
    # with the existing ix_readiness_events_agent_time (computed_at).
    op.create_index(
        "ix_readiness_events_agent_run_number",
        "agent_readiness_events",
        ["agent_id", "run_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_readiness_events_agent_run_number",
        table_name="agent_readiness_events",
    )
    for table in _TABLES:
        op.drop_column(table, "run_number")
        op.drop_column(table, "started_at")
