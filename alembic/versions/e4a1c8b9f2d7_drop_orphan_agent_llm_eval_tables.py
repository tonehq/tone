"""drop orphan agent_llm_eval tables

Three tables were left behind from an earlier draft of the agent LLM eval
feature (superseded by ``agent_llm_eval_scenarios`` + ``agent_llm_eval_results``):
``agent_llm_eval_question``, ``agent_llm_eval_run``, ``agent_llm_eval_result``
(singular). They are empty, referenced by no code, and not owned by any
current migration.

Revision ID: e4a1c8b9f2d7
Revises: 550f0ed26622
Create Date: 2026-08-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e4a1c8b9f2d7'
down_revision = '550f0ed26622'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop in FK-safe order: agent_llm_eval_result references the other two.
    op.drop_table('agent_llm_eval_result')
    op.drop_table('agent_llm_eval_run')
    op.drop_table('agent_llm_eval_question')


def downgrade() -> None:
    op.create_table(
        'agent_llm_eval_question',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_behavior', sa.Text(), nullable=True),
        sa.Column('judge_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('source_scenario_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generated_by_model', sa.String(length=120), nullable=True),
        sa.Column('generation_prompt_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_scenario_id'], ['agent_scenario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_llm_eval_question_agent_id', 'agent_llm_eval_question', ['agent_id'])
    op.create_index('ix_agent_llm_eval_question_organization_id', 'agent_llm_eval_question', ['organization_id'])
    op.create_index('ix_agent_llm_eval_question_agent_category', 'agent_llm_eval_question', ['agent_id', 'category'])
    op.create_index('ix_agent_llm_eval_question_scenario', 'agent_llm_eval_question', ['source_scenario_id'])

    op.create_table(
        'agent_llm_eval_run',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('triggered_by', sa.String(length=32), nullable=False, server_default='manual'),
        sa.Column('answer_model', sa.String(length=120), nullable=False),
        sa.Column('judge_model', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='running'),
        sa.Column('question_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pass_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fail_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('partial_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', name='uq_agent_llm_eval_run_run_id'),
    )
    op.create_index('ix_agent_llm_eval_run_agent_id', 'agent_llm_eval_run', ['agent_id'])
    op.create_index('ix_agent_llm_eval_run_organization_id', 'agent_llm_eval_run', ['organization_id'])
    op.create_index('ix_agent_llm_eval_run_agent_started', 'agent_llm_eval_run', ['agent_id', 'started_at'])

    op.create_table(
        'agent_llm_eval_result',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actual_answer', sa.Text(), nullable=True),
        sa.Column('verdict', sa.String(length=16), nullable=False),
        sa.Column('judge_reasoning', sa.Text(), nullable=True),
        sa.Column('criteria_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['agent_llm_eval_question.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_llm_eval_run.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'question_id', name='uq_agent_llm_eval_result_run_question'),
    )
    op.create_index('ix_agent_llm_eval_result_organization_id', 'agent_llm_eval_result', ['organization_id'])
    op.create_index('ix_agent_llm_eval_result_run_id', 'agent_llm_eval_result', ['run_id'])
    op.create_index('ix_agent_llm_eval_result_question_id', 'agent_llm_eval_result', ['question_id'])
