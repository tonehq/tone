"""cleanup model provider FKs — add hosting_provider_models join table, link accounts to hosting providers

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop hosting_provider_id from model_instance (derived from Account now)
    op.drop_constraint('model_instance_hosting_provider_id_fkey', 'model_instance', type_='foreignkey')
    op.drop_column('model_instance', 'hosting_provider_id')

    # 2. Drop hosting_provider_id from api_keys (linked via Account now)
    op.drop_constraint('fk_api_keys_hosting_provider_id', 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'hosting_provider_id')

    # 3. Add hosting_provider_id to accounts
    op.add_column('accounts', sa.Column('hosting_provider_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_accounts_hosting_provider_id',
        'accounts', 'hosting_providers',
        ['hosting_provider_id'], ['id'],
        ondelete='SET NULL',
    )

    # 4. Data migration: link existing accounts to hosting providers
    # For each account with model_provider_menu_id, find matching hosting_provider by name
    op.execute("""
        UPDATE accounts
        SET hosting_provider_id = hp.id
        FROM hosting_providers hp
        JOIN model_providers_menu mpm ON LOWER(hp.name) = LOWER(mpm.name)
        WHERE accounts.model_provider_menu_id = mpm.id
          AND accounts.hosting_provider_id IS NULL
    """)

    # 5. Add ondelete='SET NULL' to agent_configs model_instance FKs
    op.drop_constraint('fk_agent_configs_llm_model_instance', 'agent_configs', type_='foreignkey')
    op.drop_constraint('fk_agent_configs_tts_model_instance', 'agent_configs', type_='foreignkey')
    op.drop_constraint('fk_agent_configs_stt_model_instance', 'agent_configs', type_='foreignkey')

    op.create_foreign_key(
        'fk_agent_configs_llm_model_instance',
        'agent_configs', 'model_instance',
        ['llm_model_instance_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_agent_configs_tts_model_instance',
        'agent_configs', 'model_instance',
        ['tts_model_instance_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_agent_configs_stt_model_instance',
        'agent_configs', 'model_instance',
        ['stt_model_instance_id'], ['id'],
        ondelete='SET NULL',
    )

    # 8. Add ondelete='SET NULL' to voices new FKs
    op.drop_constraint('fk_voices_model_provider_menu_id', 'voices', type_='foreignkey')
    op.drop_constraint('fk_voices_model_menu_id', 'voices', type_='foreignkey')

    op.create_foreign_key(
        'fk_voices_model_provider_menu_id',
        'voices', 'model_providers_menu',
        ['model_provider_menu_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_voices_model_menu_id',
        'voices', 'model_menu',
        ['model_menu_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # Revert voices FKs
    op.drop_constraint('fk_voices_model_menu_id', 'voices', type_='foreignkey')
    op.drop_constraint('fk_voices_model_provider_menu_id', 'voices', type_='foreignkey')
    op.create_foreign_key(
        'fk_voices_model_provider_menu_id', 'voices', 'model_providers_menu',
        ['model_provider_menu_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_voices_model_menu_id', 'voices', 'model_menu',
        ['model_menu_id'], ['id'],
    )

    # Revert agent_configs FKs
    op.drop_constraint('fk_agent_configs_stt_model_instance', 'agent_configs', type_='foreignkey')
    op.drop_constraint('fk_agent_configs_tts_model_instance', 'agent_configs', type_='foreignkey')
    op.drop_constraint('fk_agent_configs_llm_model_instance', 'agent_configs', type_='foreignkey')
    op.create_foreign_key(
        'fk_agent_configs_llm_model_instance', 'agent_configs', 'model_instance',
        ['llm_model_instance_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_agent_configs_tts_model_instance', 'agent_configs', 'model_instance',
        ['tts_model_instance_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_agent_configs_stt_model_instance', 'agent_configs', 'model_instance',
        ['stt_model_instance_id'], ['id'],
    )

    # Drop hosting_provider_id from accounts
    op.drop_constraint('fk_accounts_hosting_provider_id', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'hosting_provider_id')

    # Re-add hosting_provider_id to api_keys
    op.add_column('api_keys', sa.Column('hosting_provider_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_api_keys_hosting_provider_id', 'api_keys', 'hosting_providers',
        ['hosting_provider_id'], ['id'], ondelete='CASCADE',
    )

    # Re-add hosting_provider_id to model_instance
    op.add_column('model_instance', sa.Column('hosting_provider_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'model_instance_hosting_provider_id_fkey', 'model_instance', 'hosting_providers',
        ['hosting_provider_id'], ['id'],
    )
