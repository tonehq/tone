"""add agent_llm_eval_runs table

Adds a dedicated runs table so an LLM eval batch is visible in the UI the
moment it's triggered — status transitions ``pending -> running ->
completed / failed`` are stored here, one row per Run Eval click. The
existing ``agent_llm_eval_results`` table is unchanged; it still holds one
row per scored scenario, keyed by the same ``run_id`` (which equals this
table's ``id``).

Backfill: for every distinct ``run_id`` already in ``agent_llm_eval_results``,
insert a corresponding ``agent_llm_eval_runs`` row with ``status='completed'``
(all historical rows finished). Derives ``run_number``, ``triggered_by``,
snapshot fields, timestamps, and ``total_scenarios = COUNT(*)`` from the
results rows. This keeps the Runs tab showing full history after the code
switches its source of truth to the new table.

Zero-blast-radius: additive table + backfill of derived data. Downgrade
drops the table; the backfilled data is derivable, so no data loss.

Revision ID: d3c8f4a1e6b9
Revises: c9e2a1f8b4d7
Create Date: 2026-08-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "d3c8f4a1e6b9"
down_revision = "c9e2a1f8b4d7"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return any(i["name"] == index for i in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_table("agent_llm_eval_runs"):
        op.create_table(
            "agent_llm_eval_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column(
                "agent_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column("run_number", sa.Integer(), nullable=False),
            sa.Column("triggered_by", sa.String(length=32), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("judge_model", sa.String(length=120), nullable=True),
            sa.Column("judge_engine", sa.String(length=32), nullable=True),
            sa.Column("llm_model", sa.String(length=120), nullable=True),
            sa.Column("llm_provider", sa.String(length=60), nullable=True),
            sa.Column(
                "total_scenarios",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "filter_snapshot",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["agent_id"], ["agents.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "agent_id",
                "run_number",
                name="uq_agent_llm_eval_runs_agent_run_number",
            ),
        )

    if not _has_index(
        "agent_llm_eval_runs", "ix_agent_llm_eval_runs_organization_id"
    ):
        op.create_index(
            "ix_agent_llm_eval_runs_organization_id",
            "agent_llm_eval_runs",
            ["organization_id"],
        )

    if not _has_index("agent_llm_eval_runs", "ix_agent_llm_eval_runs_agent_id"):
        op.create_index(
            "ix_agent_llm_eval_runs_agent_id",
            "agent_llm_eval_runs",
            ["agent_id"],
        )

    if not _has_index(
        "agent_llm_eval_runs", "ix_agent_llm_eval_runs_agent_status"
    ):
        op.create_index(
            "ix_agent_llm_eval_runs_agent_status",
            "agent_llm_eval_runs",
            ["agent_id", "status"],
        )

    if not _has_index(
        "agent_llm_eval_runs", "ix_agent_llm_eval_runs_agent_started_desc"
    ):
        op.create_index(
            "ix_agent_llm_eval_runs_agent_started_desc",
            "agent_llm_eval_runs",
            ["agent_id", "started_at"],
        )

    # Backfill historical runs so the Runs tab keeps showing full history
    # once the code switches its source of truth to this table. One row
    # per distinct ``run_id`` already in ``agent_llm_eval_results``.
    #
    # Aggregation-only fields (``total_scenarios``, ``started_at``,
    # ``completed_at``, ``created_at``, ``updated_at``) come from a
    # subquery that groups purely by ``run_id`` — even if the identity
    # columns drifted for a bug/manual-fix reason, we still get exactly
    # one aggregate row per run. Snapshot columns (org/agent/run_number/
    # triggered_by/judge_*) come from ``DISTINCT ON (run_id)`` over the
    # same table so a drifted row can't multiply and trigger the
    # ``uq_agent_llm_eval_runs_agent_run_number`` constraint. Postgres
    # can't ``MAX(uuid)`` so we can't consolidate those with the
    # aggregate subquery.
    op.execute(
        """
        WITH agg AS (
            SELECT
                run_id,
                COUNT(*) AS total_scenarios,
                MIN(started_at) AS started_at,
                MAX(completed_at) AS completed_at,
                MIN(created_at) AS created_at,
                MAX(updated_at) AS updated_at
            FROM agent_llm_eval_results
            GROUP BY run_id
        ),
        snap AS (
            SELECT DISTINCT ON (r.run_id)
                r.run_id,
                r.organization_id,
                r.agent_id,
                r.run_number,
                r.triggered_by,
                r.judge_model,
                r.judge_engine,
                r.llm_model,
                r.llm_provider
            FROM agent_llm_eval_results r
            ORDER BY r.run_id, r.created_at ASC
        )
        INSERT INTO agent_llm_eval_runs (
            id,
            organization_id,
            agent_id,
            run_number,
            triggered_by,
            status,
            judge_model,
            judge_engine,
            llm_model,
            llm_provider,
            total_scenarios,
            filter_snapshot,
            started_at,
            completed_at,
            error,
            created_at,
            updated_at
        )
        SELECT
            snap.run_id AS id,
            snap.organization_id,
            snap.agent_id,
            snap.run_number,
            snap.triggered_by,
            'completed' AS status,
            snap.judge_model,
            snap.judge_engine,
            snap.llm_model,
            snap.llm_provider,
            agg.total_scenarios,
            NULL::jsonb AS filter_snapshot,
            agg.started_at,
            agg.completed_at,
            NULL::text AS error,
            COALESCE(agg.created_at, now()) AS created_at,
            COALESCE(agg.updated_at, now()) AS updated_at
        FROM snap
        JOIN agg ON agg.run_id = snap.run_id
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    if _has_index(
        "agent_llm_eval_runs", "ix_agent_llm_eval_runs_agent_started_desc"
    ):
        op.drop_index(
            "ix_agent_llm_eval_runs_agent_started_desc",
            table_name="agent_llm_eval_runs",
        )
    if _has_index(
        "agent_llm_eval_runs", "ix_agent_llm_eval_runs_agent_status"
    ):
        op.drop_index(
            "ix_agent_llm_eval_runs_agent_status",
            table_name="agent_llm_eval_runs",
        )
    if _has_index("agent_llm_eval_runs", "ix_agent_llm_eval_runs_agent_id"):
        op.drop_index(
            "ix_agent_llm_eval_runs_agent_id",
            table_name="agent_llm_eval_runs",
        )
    if _has_index(
        "agent_llm_eval_runs", "ix_agent_llm_eval_runs_organization_id"
    ):
        op.drop_index(
            "ix_agent_llm_eval_runs_organization_id",
            table_name="agent_llm_eval_runs",
        )
    if _has_table("agent_llm_eval_runs"):
        op.drop_table("agent_llm_eval_runs")
