"""rename services to accounts and reverse api_key FK direction

Revision ID: a1b2c3d4e5f6
Revises: 0b5c01860610
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2f0435e7a13d'
down_revision = '0b5c01860610'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Rename table services -> accounts
    op.rename_table('services', 'accounts')

    # 2. Rename agent_config FK columns
    # Drop old FK constraints
    op.drop_constraint('agent_configs_llm_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_tts_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_stt_service_id_fkey', 'agent_configs', type_='foreignkey')

    # Rename columns
    op.alter_column('agent_configs', 'llm_service_id', new_column_name='llm_account_id')
    op.alter_column('agent_configs', 'tts_service_id', new_column_name='tts_account_id')
    op.alter_column('agent_configs', 'stt_service_id', new_column_name='stt_account_id')

    # Recreate FK constraints pointing to accounts
    op.create_foreign_key(
        'agent_configs_llm_account_id_fkey', 'agent_configs',
        'accounts', ['llm_account_id'], ['id']
    )
    op.create_foreign_key(
        'agent_configs_tts_account_id_fkey', 'agent_configs',
        'accounts', ['tts_account_id'], ['id']
    )
    op.create_foreign_key(
        'agent_configs_stt_account_id_fkey', 'agent_configs',
        'accounts', ['stt_account_id'], ['id']
    )

    # 3. Add account_id column to api_keys
    op.add_column('api_keys', sa.Column('account_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'api_keys_account_id_fkey', 'api_keys',
        'accounts', ['account_id'], ['id'], ondelete='SET NULL'
    )

    # 4. Data migration: copy api_key_id relationship from accounts to api_keys.account_id
    op.execute("""
        UPDATE api_keys
        SET account_id = accounts.id
        FROM accounts
        WHERE api_keys.id = accounts.api_key_id
    """)

    # 5. Drop api_key_id column from accounts
    op.drop_constraint('services_api_key_id_fkey', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'api_key_id')


def downgrade() -> None:
    # 1. Add api_key_id back to accounts
    op.add_column('accounts', sa.Column('api_key_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'services_api_key_id_fkey', 'accounts',
        'api_keys', ['api_key_id'], ['id'], ondelete='SET NULL'
    )

    # 2. Data migration: copy account_id relationship back
    op.execute("""
        UPDATE accounts
        SET api_key_id = api_keys.id
        FROM api_keys
        WHERE api_keys.account_id = accounts.id
    """)

    # 3. Drop account_id from api_keys
    op.drop_constraint('api_keys_account_id_fkey', 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'account_id')

    # 4. Rename agent_config FK columns back
    op.drop_constraint('agent_configs_llm_account_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_tts_account_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_stt_account_id_fkey', 'agent_configs', type_='foreignkey')

    op.alter_column('agent_configs', 'llm_account_id', new_column_name='llm_service_id')
    op.alter_column('agent_configs', 'tts_account_id', new_column_name='tts_service_id')
    op.alter_column('agent_configs', 'stt_account_id', new_column_name='stt_service_id')

    op.create_foreign_key(
        'agent_configs_llm_service_id_fkey', 'agent_configs',
        'services', ['llm_service_id'], ['id']
    )
    op.create_foreign_key(
        'agent_configs_tts_service_id_fkey', 'agent_configs',
        'services', ['tts_service_id'], ['id']
    )
    op.create_foreign_key(
        'agent_configs_stt_service_id_fkey', 'agent_configs',
        'services', ['stt_service_id'], ['id']
    )

    # 5. Rename table back
    op.rename_table('accounts', 'services')
