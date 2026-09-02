"""Drop unused columns: archived_at (7 tables) and models.sample_id/sample_list

These columns are dead across the whole codebase — never written, never read,
never filtered on, and never surfaced in the frontend:

- ``archived_at`` was a reserved "archive" placeholder that sat next to
  ``deleted_at`` (via ``SoftDeleteMixin`` and hand-copied onto several models).
  No archive feature was ever built, so every row is NULL. Dropped from:
  agents, agent_configs, contacts, generated_api_keys, knowledge_bases,
  uploads, workflows.
- ``models.sample_id`` / ``models.sample_list`` were leftover model-catalog
  columns with no reader or writer anywhere. Both hold only their defaults.

Verified against the target DB before writing this: all ``archived_at`` values
are NULL and no ``models`` row has a non-default sample_id/sample_list, so the
drop is data-loss-free. Downgrade re-adds the columns (empty) for reversibility.

Revision ID: f4d2a9c1e6b8
Revises: d9f4a1c7b2e5
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4d2a9c1e6b8'
down_revision = 'd9f4a1c7b2e5'
branch_labels = None
depends_on = None


# Tables that carry the now-unused ``archived_at`` column.
_ARCHIVED_AT_TABLES = (
    "agents",
    "agent_configs",
    "contacts",
    "generated_api_keys",
    "knowledge_bases",
    "uploads",
    "workflows",
)


def upgrade() -> None:
    for table in _ARCHIVED_AT_TABLES:
        op.drop_column(table, "archived_at")

    op.drop_column("models", "sample_list")
    op.drop_column("models", "sample_id")


def downgrade() -> None:
    op.add_column(
        "models",
        sa.Column("sample_id", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "models",
        sa.Column(
            "sample_list",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    for table in _ARCHIVED_AT_TABLES:
        op.add_column(
            table,
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        )
