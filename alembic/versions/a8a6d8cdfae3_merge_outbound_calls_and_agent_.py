"""merge outbound_calls and agent_readiness heads

Revision ID: a8a6d8cdfae3
Revises: b7d4e9c2f1a8, c8d1e4b7f2a3
Create Date: 2026-07-16 17:53:35.190992

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8a6d8cdfae3'
down_revision = ('b7d4e9c2f1a8', 'c8d1e4b7f2a3')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
