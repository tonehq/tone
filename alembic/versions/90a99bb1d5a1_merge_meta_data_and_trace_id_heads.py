"""merge meta_data and trace_id heads

Revision ID: 90a99bb1d5a1
Revises: eaed98724a40, c8d2e4f6a1b9
Create Date: 2026-06-02 19:07:57.332890

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90a99bb1d5a1'
down_revision = ('eaed98724a40', 'c8d2e4f6a1b9')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
