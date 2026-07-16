"""add agent readiness snapshot + event tables

Two new tables that persist the results of ``ReadinessService.check()`` runs:

- ``agent_readiness_snapshots`` — latest state per (agent, config, depth).
  UPSERTed on every run. Powers fast list badges and the edit-based
  fast-path (a snapshot with a matching ``dependency_stamp`` is
  definitionally still valid and short-circuits the runner).

- ``agent_readiness_events`` — append-only history. One row per readiness
  run. Powers audit trails and drift trends. No cron pruning in v1.

Both tables share the same column set (see
``core/models/agent_readiness_common.py::ReadinessRowMixin``); only the
uniqueness constraint differs.

Revision ID: c8d1e4b7f2a3
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c8d1e4b7f2a3"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _shared_columns() -> list:
    """Column set shared by both readiness tables.

    Kept as a function (not a module-level constant) so each ``create_table``
    call gets a fresh list of ``sa.Column`` instances — SQLAlchemy doesn't
    reuse column objects across tables.
    """
    return [
        # OrgScopedModel columns.
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Identity.
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_configs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("depth", sa.String(16), nullable=False),
        # Report summary.
        sa.Column("overall_status", sa.String(24), nullable=False),
        # All per-severity/status tallies live in one JSONB blob (mirrors
        # the API's `summary` field). Keeping them together means adding
        # a new severity later doesn't require another migration.
        sa.Column(
            "counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "checks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Provenance.
        sa.Column("trigger", sa.String(32), nullable=False),
        sa.Column(
            "triggered_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("dependency_stamp", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    # ── agent_readiness_snapshots (latest state) ──────────────────────────
    op.create_table(
        "agent_readiness_snapshots",
        *_shared_columns(),
        sa.UniqueConstraint(
            "agent_id",
            "config_id",
            "depth",
            name="uq_readiness_snapshots_agent_config_depth",
        ),
    )
    op.create_index(
        "ix_readiness_snapshots_org_agent",
        "agent_readiness_snapshots",
        ["organization_id", "agent_id"],
    )
    op.create_index(
        "ix_readiness_snapshots_org_status",
        "agent_readiness_snapshots",
        ["organization_id", "overall_status"],
    )

    # ── agent_readiness_events (append-only history) ──────────────────────
    op.create_table(
        "agent_readiness_events",
        *_shared_columns(),
    )
    op.create_index(
        "ix_readiness_events_agent_time",
        "agent_readiness_events",
        ["agent_id", "computed_at"],
    )
    op.create_index(
        "ix_readiness_events_org_time",
        "agent_readiness_events",
        ["organization_id", "computed_at"],
    )


def downgrade() -> None:
    op.drop_table("agent_readiness_events")
    op.drop_table("agent_readiness_snapshots")
