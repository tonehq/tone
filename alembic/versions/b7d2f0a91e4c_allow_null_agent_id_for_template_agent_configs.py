"""allow null agent_id for template agent_configs

Revision ID: b7d2f0a91e4c
Revises: 0cf24b3d86dc
Create Date: 2026-07-20 11:00:00.000000

Templates are reusable blueprints, not versions of a specific agent, so
``agent_configs.agent_id`` must be allowed to be NULL for template rows
(``is_template = true``). Every non-template row still requires an
``agent_id`` — enforced via a CHECK constraint so no code path can
produce an orphan non-template row.

Two DB-level changes:

1. ``ALTER COLUMN agent_id DROP NOT NULL``
2. ``ADD CONSTRAINT ck_agent_configs_agent_required_unless_template``
   ``CHECK (is_template = true OR agent_id IS NOT NULL)``

Existing rows are unaffected — they all satisfy the new CHECK because
they all currently have ``agent_id`` set.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "b7d2f0a91e4c"
down_revision = "0cf24b3d86dc"
branch_labels = None
depends_on = None


CHECK_CONSTRAINT_NAME = "ck_agent_configs_agent_required_unless_template"


def upgrade() -> None:
    op.alter_column("agent_configs", "agent_id", nullable=True)
    op.create_check_constraint(
        CHECK_CONSTRAINT_NAME,
        "agent_configs",
        "is_template = true OR agent_id IS NOT NULL",
    )


def downgrade() -> None:
    # Drop CHECK first so the NOT NULL restore can't be blocked by it.
    op.drop_constraint(CHECK_CONSTRAINT_NAME, "agent_configs", type_="check")
    # NOT NULL restore will fail if any template rows with agent_id=NULL
    # exist. Deliberate: reverting the migration should force the operator
    # to reconcile those rows first rather than silently drop them.
    op.alter_column("agent_configs", "agent_id", nullable=False)
