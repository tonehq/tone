"""Allow same phone number in multiple channels (remove phone_number unique constraint)

Revision ID: c7d8e9f0a1b2
Revises: 309524e00d5c
Create Date: 2026-02-26 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = '309524e00d5c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the global unique constraint on phone_number so that the same
    # number can be associated with multiple channels (many-to-many support).
    # The constraint was created when the table was named agent_phone_numbers,
    # so PostgreSQL kept the original auto-generated name after the rename.
    op.drop_constraint(
        'agent_phone_numbers_phone_number_key',
        'channel_phone_numbers',
        type_='unique',
    )


def downgrade() -> None:
    op.create_unique_constraint(
        'agent_phone_numbers_phone_number_key',
        'channel_phone_numbers',
        ['phone_number'],
    )
