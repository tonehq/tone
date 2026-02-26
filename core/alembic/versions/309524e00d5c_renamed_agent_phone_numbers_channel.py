"""Renamed agent phone numbers channel

Revision ID: 309524e00d5c
Revises: 1487086f6ba8
Create Date: 2026-02-26 08:51:32.979565

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '309524e00d5c'
down_revision = '1487086f6ba8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Rename table
    op.rename_table(
        "agent_phone_numbers",
        "channel_phone_numbers"
    )

    # 2. Drop FK that depends on agent_id
    op.drop_constraint(
        "agent_phone_numbers_agent_id_fkey",
        "channel_phone_numbers",
        type_="foreignkey"
    )

    # 3. Drop unique constraint that includes agent_id
    op.drop_constraint(
        "agent_phone_numbers_agent_phone_unique",
        "channel_phone_numbers",
        type_="unique"
    )

    # 4. Drop the column
    op.drop_column(
        "channel_phone_numbers",
        "agent_id"
    )

def downgrade() -> None:
    # 1. Add agent_id back
    op.add_column(
        "channel_phone_numbers",
        sa.Column("agent_id", sa.BigInteger(), nullable=False)
    )

    # 2. Restore FK
    op.create_foreign_key(
        "agent_phone_numbers_agent_id_fkey",
        "channel_phone_numbers",
        "agents",
        ["agent_id"],
        ["id"]
    )

    # 3. Restore unique constraint
    op.create_unique_constraint(
        "agent_phone_numbers_agent_phone_unique",
        "channel_phone_numbers",
        ["agent_id", "phone_number"]
    )

    # 4. Rename table back
    op.rename_table(
        "channel_phone_numbers",
        "agent_phone_numbers"
    )