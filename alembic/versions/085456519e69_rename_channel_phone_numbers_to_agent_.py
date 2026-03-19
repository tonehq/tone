"""rename channel_phone_numbers to agent_channel_phone_numbers

Revision ID: 085456519e69
Revises: f4b3860a5192
Create Date: 2026-03-18 18:16:04.018701

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '085456519e69'
down_revision = '9ddb305bedc2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename the table
    op.rename_table('channel_phone_numbers', 'agent_channel_phone_numbers')

    # Rename the unique constraint
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT channel_phone_org_unique TO agent_channel_phone_org_unique')

    # Rename the index
    op.execute('ALTER INDEX ix_channel_phone_numbers_organization_id RENAME TO ix_agent_channel_phone_numbers_organization_id')

    # Rename foreign key constraints
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT channel_phone_numbers_agent_id_fkey TO agent_channel_phone_numbers_agent_id_fkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT channel_phone_numbers_channel_id_fkey TO agent_channel_phone_numbers_channel_id_fkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT channel_phone_numbers_organization_id_fkey TO agent_channel_phone_numbers_organization_id_fkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT channel_phone_numbers_pkey TO agent_channel_phone_numbers_pkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT channel_phone_numbers_uuid_key TO agent_channel_phone_numbers_uuid_key')


def downgrade() -> None:
    # Revert constraint renames
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT agent_channel_phone_numbers_uuid_key TO channel_phone_numbers_uuid_key')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT agent_channel_phone_numbers_pkey TO channel_phone_numbers_pkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT agent_channel_phone_numbers_organization_id_fkey TO channel_phone_numbers_organization_id_fkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT agent_channel_phone_numbers_channel_id_fkey TO channel_phone_numbers_channel_id_fkey')
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT agent_channel_phone_numbers_agent_id_fkey TO channel_phone_numbers_agent_id_fkey')

    # Revert index rename
    op.execute('ALTER INDEX ix_agent_channel_phone_numbers_organization_id RENAME TO ix_channel_phone_numbers_organization_id')

    # Revert unique constraint rename
    op.execute('ALTER TABLE agent_channel_phone_numbers RENAME CONSTRAINT agent_channel_phone_org_unique TO channel_phone_org_unique')

    # Revert table rename
    op.rename_table('agent_channel_phone_numbers', 'channel_phone_numbers')
