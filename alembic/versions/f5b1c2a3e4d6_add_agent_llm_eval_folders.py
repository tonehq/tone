"""add agent_llm_eval_folders + swap scenarios.folder → folder_id FK

Folders become first-class rows: the derived VARCHAR ``folder`` column on
``agent_llm_eval_scenarios`` is replaced with a NOT NULL FK to the new
``agent_llm_eval_folders`` table (ON DELETE CASCADE — deleting a folder
removes every scenario inside it, matching the shipped UX).

``agent_llm_eval_results.folder`` (the run-time snapshot) is UNCHANGED so
historical run rows keep the folder name they were scored under even after
the source folder is renamed or deleted.

Data note: staging data was truncated before this change, so no backfill
is needed. Downgrade re-adds the VARCHAR column but the FK data is lost.

Revision ID: f5b1c2a3e4d6
Revises: d3c8f4a1e6b9
Create Date: 2026-08-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "f5b1c2a3e4d6"
down_revision = "d3c8f4a1e6b9"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return any(i["name"] == index for i in inspect(op.get_bind()).get_indexes(table))


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def _has_foreign_key(table: str, fk_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        fk.get("name") == fk_name
        for fk in inspect(op.get_bind()).get_foreign_keys(table)
    )


def upgrade() -> None:
    # 1. Create the new folders table.
    if not _has_table("agent_llm_eval_folders"):
        op.create_table(
            "agent_llm_eval_folders",
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
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
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
                "name",
                name="uq_agent_llm_eval_folders_agent_name",
            ),
        )

    if not _has_index(
        "agent_llm_eval_folders", "ix_agent_llm_eval_folders_organization_id"
    ):
        op.create_index(
            "ix_agent_llm_eval_folders_organization_id",
            "agent_llm_eval_folders",
            ["organization_id"],
        )

    if not _has_index(
        "agent_llm_eval_folders", "ix_agent_llm_eval_folders_agent"
    ):
        op.create_index(
            "ix_agent_llm_eval_folders_agent",
            "agent_llm_eval_folders",
            ["agent_id"],
        )

    # 2. Drop the old partial index that filtered on scenarios.folder — the
    # column itself is about to go away. Same for the results-side partial
    # index (kept the VARCHAR column but the index isn't useful anymore).
    if _has_index(
        "agent_llm_eval_scenarios",
        "ix_agent_llm_eval_scenarios_agent_folder",
    ):
        op.drop_index(
            "ix_agent_llm_eval_scenarios_agent_folder",
            table_name="agent_llm_eval_scenarios",
        )

    # 3. Drop the old VARCHAR ``folder`` column on scenarios. Data was
    # truncated pre-migration so no backfill is needed.
    if _has_column("agent_llm_eval_scenarios", "folder"):
        op.drop_column("agent_llm_eval_scenarios", "folder")

    # 4. Add ``folder_id`` FK column — nullable at first so the ALTER can
    # succeed even against a live table (empty in staging; hypothetical
    # rows in some other environment can be backfilled here later). The
    # matching NOT NULL is applied in step 5.
    if not _has_column("agent_llm_eval_scenarios", "folder_id"):
        op.add_column(
            "agent_llm_eval_scenarios",
            sa.Column(
                "folder_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )

    # 4b. Create the FK separately — an interrupted prior run that added
    # the column but crashed before the FK would otherwise leave the
    # constraint permanently missing (the outer `if not _has_column` gate
    # would skip the whole block on re-run). Guarding the FK by its own
    # inspector check makes the migration re-runnable.
    if not _has_foreign_key(
        "agent_llm_eval_scenarios", "fk_agent_llm_eval_scenarios_folder"
    ):
        op.create_foreign_key(
            "fk_agent_llm_eval_scenarios_folder",
            "agent_llm_eval_scenarios",
            "agent_llm_eval_folders",
            ["folder_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # 5. Flip to NOT NULL — staging is empty so this is safe. Any environment
    # with data must backfill before running this migration (see the seed
    # script ``dev/seed_default_folders.py`` for a matching agent-side seed).
    op.alter_column(
        "agent_llm_eval_scenarios",
        "folder_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    if not _has_index(
        "agent_llm_eval_scenarios", "ix_agent_llm_eval_scenarios_folder_id"
    ):
        op.create_index(
            "ix_agent_llm_eval_scenarios_folder_id",
            "agent_llm_eval_scenarios",
            ["folder_id"],
        )

    # 6. ``agent_llm_eval_results.folder`` is INTENTIONALLY left as-is —
    # it's a text snapshot column stored at scoring time so history renders
    # correctly even after the source folder is renamed or deleted. No
    # schema change here.


def downgrade() -> None:
    # Re-add the old VARCHAR ``folder`` column on scenarios (data lost) and
    # drop the folders table + FK column.
    if _has_index(
        "agent_llm_eval_scenarios", "ix_agent_llm_eval_scenarios_folder_id"
    ):
        op.drop_index(
            "ix_agent_llm_eval_scenarios_folder_id",
            table_name="agent_llm_eval_scenarios",
        )

    if _has_column("agent_llm_eval_scenarios", "folder_id"):
        try:
            op.drop_constraint(
                "fk_agent_llm_eval_scenarios_folder",
                "agent_llm_eval_scenarios",
                type_="foreignkey",
            )
        except Exception:  # noqa: BLE001
            # Constraint may already be gone; keep going.
            pass
        op.drop_column("agent_llm_eval_scenarios", "folder_id")

    if not _has_column("agent_llm_eval_scenarios", "folder"):
        op.add_column(
            "agent_llm_eval_scenarios",
            sa.Column("folder", sa.String(length=120), nullable=True),
        )
        op.create_index(
            "ix_agent_llm_eval_scenarios_agent_folder",
            "agent_llm_eval_scenarios",
            ["agent_id", "folder"],
            postgresql_where=sa.text("folder IS NOT NULL"),
        )

    if _has_index(
        "agent_llm_eval_folders", "ix_agent_llm_eval_folders_agent"
    ):
        op.drop_index(
            "ix_agent_llm_eval_folders_agent",
            table_name="agent_llm_eval_folders",
        )
    if _has_index(
        "agent_llm_eval_folders", "ix_agent_llm_eval_folders_organization_id"
    ):
        op.drop_index(
            "ix_agent_llm_eval_folders_organization_id",
            table_name="agent_llm_eval_folders",
        )
    if _has_table("agent_llm_eval_folders"):
        op.drop_table("agent_llm_eval_folders")
