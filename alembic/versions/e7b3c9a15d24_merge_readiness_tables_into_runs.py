"""merge readiness snapshot + event tables into a single agent_readiness_runs

Collapses the former two-table readiness design into ONE append-only table:

- ``agent_readiness_snapshots`` (latest-only, UPSERTed) is renamed to
  ``agent_readiness_runs`` and its latest-only uniqueness is dropped so it can
  hold history too.
- ``agent_readiness_events`` (append-only history) is folded in — its non-latest
  rows are copied over first so NO history is lost — then dropped.

After this, "latest state" is just the most recent row per (agent, config,
depth) and "history" is the full row set. See
``core/models/agent_readiness_run.py``.

Revision ID: e7b3c9a15d24
Revises: f5b1c2a3e4d6
Create Date: 2026-09-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e7b3c9a15d24"
down_revision = "f5b1c2a3e4d6"
branch_labels = None
depends_on = None


# Explicit column list shared by the data-copy statements and the downgrade's
# events-table recreate — one source of truth so the two can never drift.
_COLS = [
    "id", "organization_id", "created_at", "updated_at", "agent_id",
    "config_id", "depth", "overall_status", "counts", "checks", "trigger",
    "triggered_by_user_id", "duration_ms", "started_at", "computed_at",
    "run_number", "name", "dependency_stamp", "error",
]


def _csv(prefix: str = "") -> str:
    """Comma-joined column list, optionally alias-prefixed (e.g. ``e.``)."""
    return ", ".join(f"{prefix}{c}" for c in _COLS)


def _readiness_columns() -> list:
    """Full column set for the readiness tables (used to recreate the events
    table on downgrade). Fresh ``sa.Column`` objects per call — SQLAlchemy
    doesn't reuse column instances across tables."""
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "agent_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column(
            "config_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=True,
        ),
        sa.Column("depth", sa.String(16), nullable=False),
        sa.Column("overall_status", sa.String(24), nullable=False),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("trigger", sa.String(32), nullable=False),
        sa.Column(
            "triggered_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("run_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("dependency_stamp", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    # 1. Snapshots becomes the single append-only runs table — drop the
    #    latest-only uniqueness so it can hold multiple rows per tuple.
    op.drop_constraint(
        "uq_readiness_snapshots_agent_config_depth",
        "agent_readiness_snapshots",
        type_="unique",
    )

    # 2. Preserve history: copy the NON-latest event rows in. The latest row
    #    per (agent, config, depth) already lives in snapshots (both tables were
    #    written together), so we insert only events that have a later sibling.
    op.execute(
        f"""
        INSERT INTO agent_readiness_snapshots ({_csv()})
        SELECT {_csv("e.")}
        FROM agent_readiness_events e
        WHERE EXISTS (
            SELECT 1 FROM agent_readiness_events e2
            WHERE e2.agent_id = e.agent_id
              AND e2.config_id IS NOT DISTINCT FROM e.config_id
              AND e2.depth = e.depth
              AND e2.computed_at > e.computed_at
        )
        """
    )

    # 3. Drop the now-redundant history table (its indexes drop with it).
    op.drop_table("agent_readiness_events")

    # 4. Rename the table + its constraint/indexes to the runs naming.
    op.rename_table("agent_readiness_snapshots", "agent_readiness_runs")
    op.execute(
        "ALTER TABLE agent_readiness_runs "
        "RENAME CONSTRAINT agent_readiness_snapshots_pkey TO agent_readiness_runs_pkey"
    )
    op.execute("ALTER INDEX ix_agent_readiness_snapshots_organization_id RENAME TO ix_agent_readiness_runs_organization_id")
    op.execute("ALTER INDEX ix_agent_readiness_snapshots_agent_id RENAME TO ix_agent_readiness_runs_agent_id")
    op.execute("ALTER INDEX ix_readiness_snapshots_org_agent RENAME TO ix_readiness_runs_org_agent")
    op.execute("ALTER INDEX ix_readiness_snapshots_org_status RENAME TO ix_readiness_runs_org_status")

    # 5. Add the indexes the append-only "latest" + history access patterns need.
    op.create_index("ix_readiness_runs_agent_time", "agent_readiness_runs", ["agent_id", "computed_at"])
    op.create_index(
        "ix_readiness_runs_agent_config_depth_time",
        "agent_readiness_runs",
        ["agent_id", "config_id", "depth", "computed_at"],
    )
    op.create_index("ix_readiness_runs_org_time", "agent_readiness_runs", ["organization_id", "computed_at"])


def downgrade() -> None:
    # Reverse: split the single runs table back into snapshots (latest) + events
    # (history). Best-effort — history is reconstructed from the merged rows.

    # 1. Drop the append-only-only indexes.
    op.drop_index("ix_readiness_runs_org_time", table_name="agent_readiness_runs")
    op.drop_index("ix_readiness_runs_agent_config_depth_time", table_name="agent_readiness_runs")
    op.drop_index("ix_readiness_runs_agent_time", table_name="agent_readiness_runs")

    # 2. Recreate the append-only events table + its indexes and copy the FULL
    #    history from runs into it.
    op.create_table("agent_readiness_events", *_readiness_columns())
    op.create_index("ix_readiness_events_agent_time", "agent_readiness_events", ["agent_id", "computed_at"])
    op.create_index("ix_readiness_events_org_time", "agent_readiness_events", ["organization_id", "computed_at"])
    op.execute(
        f"""
        INSERT INTO agent_readiness_events ({_csv()})
        SELECT {_csv("r.")}
        FROM agent_readiness_runs r
        """
    )

    # 3. Reduce runs back to latest-per-tuple, rename it back to snapshots, and
    #    restore the latest-only uniqueness.
    op.execute(
        """
        DELETE FROM agent_readiness_runs r
        WHERE EXISTS (
            SELECT 1 FROM agent_readiness_runs r2
            WHERE r2.agent_id = r.agent_id
              AND r2.config_id IS NOT DISTINCT FROM r.config_id
              AND r2.depth = r.depth
              AND r2.computed_at > r.computed_at
        )
        """
    )
    op.execute("ALTER INDEX ix_readiness_runs_org_status RENAME TO ix_readiness_snapshots_org_status")
    op.execute("ALTER INDEX ix_readiness_runs_org_agent RENAME TO ix_readiness_snapshots_org_agent")
    op.execute("ALTER INDEX ix_agent_readiness_runs_agent_id RENAME TO ix_agent_readiness_snapshots_agent_id")
    op.execute("ALTER INDEX ix_agent_readiness_runs_organization_id RENAME TO ix_agent_readiness_snapshots_organization_id")
    op.execute(
        "ALTER TABLE agent_readiness_runs "
        "RENAME CONSTRAINT agent_readiness_runs_pkey TO agent_readiness_snapshots_pkey"
    )
    op.rename_table("agent_readiness_runs", "agent_readiness_snapshots")
    op.create_unique_constraint(
        "uq_readiness_snapshots_agent_config_depth",
        "agent_readiness_snapshots",
        ["agent_id", "config_id", "depth"],
    )
