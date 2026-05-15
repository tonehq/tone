"""add model_instance_ids to agent_configs

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agent_configs', sa.Column('llm_model_instance_id', sa.BigInteger(), nullable=True))
    op.add_column('agent_configs', sa.Column('tts_model_instance_id', sa.BigInteger(), nullable=True))
    op.add_column('agent_configs', sa.Column('stt_model_instance_id', sa.BigInteger(), nullable=True))

    op.create_foreign_key(
        'fk_agent_configs_llm_model_instance',
        'agent_configs', 'model_instance',
        ['llm_model_instance_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_agent_configs_tts_model_instance',
        'agent_configs', 'model_instance',
        ['tts_model_instance_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_agent_configs_stt_model_instance',
        'agent_configs', 'model_instance',
        ['stt_model_instance_id'], ['id'],
    )

    op.create_index('ix_agent_configs_llm_model_instance_id', 'agent_configs', ['llm_model_instance_id'])
    op.create_index('ix_agent_configs_tts_model_instance_id', 'agent_configs', ['tts_model_instance_id'])
    op.create_index('ix_agent_configs_stt_model_instance_id', 'agent_configs', ['stt_model_instance_id'])


def downgrade() -> None:
    op.drop_index('ix_agent_configs_stt_model_instance_id', table_name='agent_configs')
    op.drop_index('ix_agent_configs_tts_model_instance_id', table_name='agent_configs')
    op.drop_index('ix_agent_configs_llm_model_instance_id', table_name='agent_configs')

    op.drop_constraint('fk_agent_configs_stt_model_instance', 'agent_configs', type_='foreignkey')
    op.drop_constraint('fk_agent_configs_tts_model_instance', 'agent_configs', type_='foreignkey')
    op.drop_constraint('fk_agent_configs_llm_model_instance', 'agent_configs', type_='foreignkey')

    op.drop_column('agent_configs', 'stt_model_instance_id')
    op.drop_column('agent_configs', 'tts_model_instance_id')
    op.drop_column('agent_configs', 'llm_model_instance_id')
