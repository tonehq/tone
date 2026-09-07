"""agent-LLM eval versioning + single-table folder tree

Two changes to the agent-LLM eval domain:

1. **Versioning** — new ``agent_llm_eval_scenario_versions`` table; scenarios
   gain ``version_id`` (nullable) + ``approval_status`` (default 'approved').
   ``agent_llm_eval_runs`` / ``agent_llm_eval_results`` gain a ``version_id``
   snapshot (``ON DELETE SET NULL`` so run history survives version delete).
   No version backfill — existing scenarios stay ``version_id=NULL`` /
   ``approval_status='approved'``.

2. **Folder tree collapse** — ``agent_llm_eval_folders`` folds into
   ``agent_llm_eval_scenarios`` as ``node_type='folder'`` rows in an adjacency
   tree (``parent_id`` self-FK). Existing folder rows are copied in (reusing
   their id as the node id) and each scenario's ``folder_id`` is repointed to
   ``parent_id``; the old table + ``folder_id`` column are then dropped.

PG14-safe uniqueness (no ``NULLS NOT DISTINCT`` — that's PG15+): split into
partial unique indexes whose predicates keep NULLs out of the indexed columns.

Revision ID: e2f8a1c4b7d3
Revises: f3b8d1e0c6a9
Create Date: 2026-09-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "e2f8a1c4b7d3"
down_revision = "f3b8d1e0c6a9"
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


def _has_unique_constraint(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        uc.get("name") == name
        for uc in inspect(op.get_bind()).get_unique_constraints(table)
    )


_SCENARIOS = "agent_llm_eval_scenarios"
_VERSIONS = "agent_llm_eval_scenario_versions"
_FOLDERS = "agent_llm_eval_folders"


def upgrade() -> None:
    # 1. Version parent table.
    if not _has_table(_VERSIONS):
        op.create_table(
            _VERSIONS,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=16), nullable=False, server_default=sa.text("'generated'")),
            sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'draft'")),
            sa.Column("generation_prompt", sa.Text(), nullable=True),
            sa.Column("generated_by_model", sa.String(length=120), nullable=True),
            sa.Column("generation_prompt_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("agent_id", "version_number", name="uq_agent_llm_eval_scenario_versions_agent_number"),
        )
    if not _has_index(_VERSIONS, "ix_agent_llm_eval_scenario_versions_organization_id"):
        op.create_index("ix_agent_llm_eval_scenario_versions_organization_id", _VERSIONS, ["organization_id"])
    if not _has_index(_VERSIONS, "ix_agent_llm_eval_scenario_versions_agent"):
        op.create_index("ix_agent_llm_eval_scenario_versions_agent", _VERSIONS, ["agent_id"])

    # 2. New columns on scenarios (additive; server_defaults keep old rows valid).
    if not _has_column(_SCENARIOS, "node_type"):
        op.add_column(_SCENARIOS, sa.Column("node_type", sa.String(length=16), nullable=False, server_default=sa.text("'scenario'")))
    if not _has_column(_SCENARIOS, "parent_id"):
        op.add_column(_SCENARIOS, sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _has_column(_SCENARIOS, "name"):
        op.add_column(_SCENARIOS, sa.Column("name", sa.String(length=120), nullable=True))
    if not _has_column(_SCENARIOS, "version_id"):
        op.add_column(_SCENARIOS, sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _has_column(_SCENARIOS, "approval_status"):
        op.add_column(_SCENARIOS, sa.Column("approval_status", sa.String(length=16), nullable=False, server_default=sa.text("'approved'")))
    # Folder nodes carry no prompt / scenario_key.
    op.alter_column(_SCENARIOS, "prompt", existing_type=sa.Text(), nullable=True)
    op.alter_column(_SCENARIOS, "scenario_key", existing_type=sa.String(length=120), nullable=True)
    # Drop the NOT NULL on the (soon-to-be-removed) folder_id BEFORE the folder
    # data-move inserts folder nodes with a NULL folder_id — otherwise the
    # still-present NOT NULL constraint rejects them. The column itself is
    # dropped in step 5.
    if _has_column(_SCENARIOS, "folder_id"):
        op.alter_column(
            _SCENARIOS, "folder_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True
        )

    # 3. FKs (self-referential parent + version).
    if not _has_foreign_key(_SCENARIOS, "fk_agent_llm_eval_scenarios_parent"):
        op.create_foreign_key(
            "fk_agent_llm_eval_scenarios_parent",
            _SCENARIOS, _SCENARIOS, ["parent_id"], ["id"], ondelete="CASCADE",
        )
    if not _has_foreign_key(_SCENARIOS, "fk_agent_llm_eval_scenarios_version"):
        op.create_foreign_key(
            "fk_agent_llm_eval_scenarios_version",
            _SCENARIOS, _VERSIONS, ["version_id"], ["id"], ondelete="CASCADE",
        )

    # 4. One-time folder → tree data move (reuse folder id as the node id).
    if _has_table(_FOLDERS):
        op.execute(
            """
            INSERT INTO agent_llm_eval_scenarios
                (id, organization_id, agent_id, node_type, name, approval_status,
                 scenario_ord, source, created_at, updated_at)
            SELECT id, organization_id, agent_id, 'folder', name, 'approved',
                   0, 'manual', created_at, updated_at
            FROM agent_llm_eval_folders
            """
        )
        op.execute(
            """
            UPDATE agent_llm_eval_scenarios
            SET parent_id = folder_id
            WHERE node_type = 'scenario' AND parent_id IS NULL
            """
        )

    # 5. Contract: drop the old folder linkage + table.
    if _has_foreign_key(_SCENARIOS, "fk_agent_llm_eval_scenarios_folder"):
        op.drop_constraint("fk_agent_llm_eval_scenarios_folder", _SCENARIOS, type_="foreignkey")
    if _has_index(_SCENARIOS, "ix_agent_llm_eval_scenarios_folder_id"):
        op.drop_index("ix_agent_llm_eval_scenarios_folder_id", table_name=_SCENARIOS)
    if _has_unique_constraint(_SCENARIOS, "uq_agent_llm_eval_scenarios_agent_key"):
        op.drop_constraint("uq_agent_llm_eval_scenarios_agent_key", _SCENARIOS, type_="unique")
    if _has_column(_SCENARIOS, "folder_id"):
        op.drop_column(_SCENARIOS, "folder_id")
    if _has_table(_FOLDERS):
        op.drop_table(_FOLDERS)

    # 6. CHECK — a scenario node must have a prompt; a folder node need not.
    op.create_check_constraint(
        "ck_agent_llm_eval_scenarios_prompt_required",
        _SCENARIOS,
        "node_type = 'folder' OR prompt IS NOT NULL",
    )

    # 7. Partial unique indexes (PG14-safe) + read indexes.
    if not _has_index(_SCENARIOS, "uq_agent_llm_eval_scenarios_folder_root"):
        op.create_index(
            "uq_agent_llm_eval_scenarios_folder_root", _SCENARIOS, ["agent_id", "name"],
            unique=True, postgresql_where=sa.text("node_type = 'folder' AND parent_id IS NULL"),
        )
    if not _has_index(_SCENARIOS, "uq_agent_llm_eval_scenarios_folder_child"):
        op.create_index(
            "uq_agent_llm_eval_scenarios_folder_child", _SCENARIOS, ["agent_id", "parent_id", "name"],
            unique=True, postgresql_where=sa.text("node_type = 'folder' AND parent_id IS NOT NULL"),
        )
    if not _has_index(_SCENARIOS, "uq_agent_llm_eval_scenarios_versionless"):
        op.create_index(
            "uq_agent_llm_eval_scenarios_versionless", _SCENARIOS, ["agent_id", "scenario_key"],
            unique=True, postgresql_where=sa.text("node_type = 'scenario' AND version_id IS NULL"),
        )
    if not _has_index(_SCENARIOS, "uq_agent_llm_eval_scenarios_versioned"):
        op.create_index(
            "uq_agent_llm_eval_scenarios_versioned", _SCENARIOS, ["agent_id", "version_id", "scenario_key"],
            unique=True, postgresql_where=sa.text("node_type = 'scenario' AND version_id IS NOT NULL"),
        )
    if not _has_index(_SCENARIOS, "ix_agent_llm_eval_scenarios_parent"):
        op.create_index("ix_agent_llm_eval_scenarios_parent", _SCENARIOS, ["parent_id"])
    if not _has_index(_SCENARIOS, "ix_agent_llm_eval_scenarios_version_id"):
        op.create_index("ix_agent_llm_eval_scenarios_version_id", _SCENARIOS, ["version_id"])

    # 8. Runs: version stamp.
    if not _has_column("agent_llm_eval_runs", "version_id"):
        op.add_column("agent_llm_eval_runs", sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_agent_llm_eval_runs_version",
            "agent_llm_eval_runs", _VERSIONS, ["version_id"], ["id"], ondelete="SET NULL",
        )
        op.create_index("ix_agent_llm_eval_runs_version_id", "agent_llm_eval_runs", ["version_id"])

    # 9. Results: version stamp (snapshot; SET NULL so history survives).
    if not _has_column("agent_llm_eval_results", "version_id"):
        op.add_column("agent_llm_eval_results", sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_agent_llm_eval_results_version",
            "agent_llm_eval_results", _VERSIONS, ["version_id"], ["id"], ondelete="SET NULL",
        )
        op.create_index("ix_agent_llm_eval_results_version_id", "agent_llm_eval_results", ["version_id"])


def downgrade() -> None:
    # Best-effort inverse (one-shot contract is not fully rollback-clean).
    # Results / runs version stamp.
    if _has_index("agent_llm_eval_results", "ix_agent_llm_eval_results_version_id"):
        op.drop_index("ix_agent_llm_eval_results_version_id", table_name="agent_llm_eval_results")
    if _has_foreign_key("agent_llm_eval_results", "fk_agent_llm_eval_results_version"):
        op.drop_constraint("fk_agent_llm_eval_results_version", "agent_llm_eval_results", type_="foreignkey")
    if _has_column("agent_llm_eval_results", "version_id"):
        op.drop_column("agent_llm_eval_results", "version_id")
    if _has_index("agent_llm_eval_runs", "ix_agent_llm_eval_runs_version_id"):
        op.drop_index("ix_agent_llm_eval_runs_version_id", table_name="agent_llm_eval_runs")
    if _has_foreign_key("agent_llm_eval_runs", "fk_agent_llm_eval_runs_version"):
        op.drop_constraint("fk_agent_llm_eval_runs_version", "agent_llm_eval_runs", type_="foreignkey")
    if _has_column("agent_llm_eval_runs", "version_id"):
        op.drop_column("agent_llm_eval_runs", "version_id")

    # Drop the tree indexes + CHECK.
    for idx in (
        "uq_agent_llm_eval_scenarios_folder_root",
        "uq_agent_llm_eval_scenarios_folder_child",
        "uq_agent_llm_eval_scenarios_versionless",
        "uq_agent_llm_eval_scenarios_versioned",
        "ix_agent_llm_eval_scenarios_parent",
        "ix_agent_llm_eval_scenarios_version_id",
    ):
        if _has_index(_SCENARIOS, idx):
            op.drop_index(idx, table_name=_SCENARIOS)
    op.drop_constraint("ck_agent_llm_eval_scenarios_prompt_required", _SCENARIOS, type_="check")

    # Recreate the folders table + folder_id column, backfill from folder nodes.
    if not _has_table(_FOLDERS):
        op.create_table(
            _FOLDERS,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("agent_id", "name", name="uq_agent_llm_eval_folders_agent_name"),
        )
        op.execute(
            """
            INSERT INTO agent_llm_eval_folders
                (id, organization_id, agent_id, name, created_at, updated_at)
            SELECT id, organization_id, agent_id, name, created_at, updated_at
            FROM agent_llm_eval_scenarios WHERE node_type = 'folder'
            """
        )
    if not _has_column(_SCENARIOS, "folder_id"):
        op.add_column(_SCENARIOS, sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.execute("UPDATE agent_llm_eval_scenarios SET folder_id = parent_id WHERE node_type = 'scenario'")
    # Remove folder nodes now that they live back in their own table.
    op.execute("DELETE FROM agent_llm_eval_scenarios WHERE node_type = 'folder'")

    # Drop the new scenario columns + FKs.
    if _has_foreign_key(_SCENARIOS, "fk_agent_llm_eval_scenarios_version"):
        op.drop_constraint("fk_agent_llm_eval_scenarios_version", _SCENARIOS, type_="foreignkey")
    if _has_foreign_key(_SCENARIOS, "fk_agent_llm_eval_scenarios_parent"):
        op.drop_constraint("fk_agent_llm_eval_scenarios_parent", _SCENARIOS, type_="foreignkey")
    for col in ("version_id", "approval_status", "name", "parent_id", "node_type"):
        if _has_column(_SCENARIOS, col):
            op.drop_column(_SCENARIOS, col)

    # Restore folder_id FK + NOT NULLs + old unique constraint.
    if not _has_foreign_key(_SCENARIOS, "fk_agent_llm_eval_scenarios_folder"):
        op.create_foreign_key(
            "fk_agent_llm_eval_scenarios_folder",
            _SCENARIOS, _FOLDERS, ["folder_id"], ["id"], ondelete="CASCADE",
        )
    if not _has_index(_SCENARIOS, "ix_agent_llm_eval_scenarios_folder_id"):
        op.create_index("ix_agent_llm_eval_scenarios_folder_id", _SCENARIOS, ["folder_id"])
    op.alter_column(_SCENARIOS, "prompt", existing_type=sa.Text(), nullable=False)
    op.alter_column(_SCENARIOS, "scenario_key", existing_type=sa.String(length=120), nullable=False)
    if not _has_unique_constraint(_SCENARIOS, "uq_agent_llm_eval_scenarios_agent_key"):
        op.create_unique_constraint(
            "uq_agent_llm_eval_scenarios_agent_key", _SCENARIOS, ["agent_id", "scenario_key"]
        )

    if _has_index(_VERSIONS, "ix_agent_llm_eval_scenario_versions_agent"):
        op.drop_index("ix_agent_llm_eval_scenario_versions_agent", table_name=_VERSIONS)
    if _has_index(_VERSIONS, "ix_agent_llm_eval_scenario_versions_organization_id"):
        op.drop_index("ix_agent_llm_eval_scenario_versions_organization_id", table_name=_VERSIONS)
    if _has_table(_VERSIONS):
        op.drop_table(_VERSIONS)
