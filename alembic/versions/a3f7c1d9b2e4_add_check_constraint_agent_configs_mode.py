"""Add CHECK constraint restricting agent_configs.mode to prompt/workflow

``agent_configs.mode`` drives the conversation flow and is only ever ``prompt``
or ``workflow``. The API request schema already enforces this
(``Literal["prompt", "workflow"]``); this constraint mirrors that guarantee at
the DB level so no path (script, backfill, manual insert) can persist an
out-of-set value.

Behavior-preserving: verified against the target DB that every existing row is
already ``prompt`` or ``workflow``, and the create path only ever writes those
two values, so no existing or app-driven write can violate it.

NOTE: this revision has intentionally NOT been applied to any database yet —
it ships as a pending migration to be run via the normal ``alembic upgrade``
flow per environment.

Revision ID: a3f7c1d9b2e4
Revises: e7b1c4a9d3f2
Create Date: 2026-09-02

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a3f7c1d9b2e4'
down_revision = 'e7b1c4a9d3f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_agent_configs_mode_valid",
        "agent_configs",
        "mode IN ('prompt', 'workflow')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_agent_configs_mode_valid", "agent_configs", type_="check"
    )
