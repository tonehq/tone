"""drop_invite_email_unique_constraint

Revision ID: f1a2b3c4d5e6
Revises: e268c5acbe84
Create Date: 2026-03-10 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e268c5acbe84'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('invite_email_unique', 'organization_invites', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint('invite_email_unique', 'organization_invites', ['email'])
