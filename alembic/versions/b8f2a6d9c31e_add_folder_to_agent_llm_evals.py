"""add folder column to agent_llm_eval scenarios + results

Adds a nullable ``folder VARCHAR(120)`` to both ``agent_llm_eval_scenarios``
and ``agent_llm_eval_results`` so scenarios can be grouped into user-named
suites (e.g. "Refund flow", "Objection handling"). Snapshotting the folder
name onto ``agent_llm_eval_results`` mirrors how ``scenario_tags`` /
``prompt`` / ``expected_answer`` are already snapshotted — a rename bulk-
updates BOTH tables in one transaction so past runs stay grouped under the
current name.

Partial indexes on ``(agent_id, folder) WHERE folder IS NOT NULL`` keep the
"list distinct folders per agent" query cheap without weighing down inserts
for the null (Uncategorized) case.

Revision ID: b8f2a6d9c31e
Revises: e4a1c8b9f2d7
Create Date: 2026-08-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8f2a6d9c31e'
down_revision = 'e4a1c8b9f2d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'agent_llm_eval_scenarios',
        sa.Column('folder', sa.String(length=120), nullable=True),
    )
    op.add_column(
        'agent_llm_eval_results',
        sa.Column('folder', sa.String(length=120), nullable=True),
    )
    op.create_index(
        'ix_agent_llm_eval_scenarios_agent_folder',
        'agent_llm_eval_scenarios',
        ['agent_id', 'folder'],
        postgresql_where=sa.text('folder IS NOT NULL'),
    )
    op.create_index(
        'ix_agent_llm_eval_results_agent_folder',
        'agent_llm_eval_results',
        ['agent_id', 'folder'],
        postgresql_where=sa.text('folder IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_agent_llm_eval_results_agent_folder',
        table_name='agent_llm_eval_results',
    )
    op.drop_index(
        'ix_agent_llm_eval_scenarios_agent_folder',
        table_name='agent_llm_eval_scenarios',
    )
    op.drop_column('agent_llm_eval_results', 'folder')
    op.drop_column('agent_llm_eval_scenarios', 'folder')
