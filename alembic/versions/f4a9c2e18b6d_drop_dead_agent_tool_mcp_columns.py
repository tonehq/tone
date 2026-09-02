"""Drop dead/unused columns on agents, agent_configs, tools, mcp_servers

Removes eight columns that are not read by the runtime voice pipeline and
carry no behavior. Audited on branch ``agent-config-analysis``:

- ``agents.llm_model`` — never written by any create path; the LLM is
  resolved from ``agent_configs.llm_settings.model_id`` at call time. Was only
  a legacy display fallback in ``AgentService.agent_response`` (now removed).
- ``agent_configs.canvas_label`` — only ever appeared in the model
  definition; no reader, writer, request schema, or UI.
- ``agent_configs.knowledge_model_id`` — never consulted at call time; KB
  retrieval uses the ingestion run's embedding provider/model/dimensions. The
  UI only ever sent ``null``. Had a SET NULL FK to ``models.id``.
- ``agent_configs.conversation_history_token_limit`` — stored via the API but
  no runtime consumer and no real UI input.
- ``tools.action_params_schema`` / ``tools.trigger_phrases`` /
  ``tools.entity`` — only ever appeared in the model definition; no reader,
  writer, request schema, or UI.
- ``mcp_servers.endpoint`` — stored via the API but the MCP connection uses
  ``server_url`` (``resolve_server_url``); ``endpoint`` is never used to
  connect.

Behavior-preserving: none of these columns feed a live call. The matching
model mappings, request schemas, serializers, and frontend types/form fields
are removed in the same change, so the app no longer references them.

NOTE: this revision has intentionally NOT been applied to any database yet —
it ships as a pending migration to be run via the normal ``alembic upgrade``
flow per environment. Verify no non-null values are needed before applying.

Revision ID: f4a9c2e18b6d
Revises: a3f7c1d9b2e4
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f4a9c2e18b6d'
down_revision = 'a3f7c1d9b2e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agents
    op.drop_column('agents', 'llm_model')

    # agent_configs (dropping knowledge_model_id also drops its FK to models)
    op.drop_column('agent_configs', 'canvas_label')
    op.drop_column('agent_configs', 'knowledge_model_id')
    op.drop_column('agent_configs', 'conversation_history_token_limit')

    # tools
    op.drop_column('tools', 'action_params_schema')
    op.drop_column('tools', 'trigger_phrases')
    op.drop_column('tools', 'entity')

    # mcp_servers
    op.drop_column('mcp_servers', 'endpoint')


def downgrade() -> None:
    # mcp_servers
    op.add_column(
        'mcp_servers',
        sa.Column('endpoint', sa.String(length=500), nullable=True),
    )

    # tools
    op.add_column('tools', sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tools', sa.Column('trigger_phrases', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tools', sa.Column('action_params_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # agent_configs
    op.add_column(
        'agent_configs',
        sa.Column('conversation_history_token_limit', sa.Integer(), nullable=True),
    )
    op.add_column(
        'agent_configs',
        sa.Column('knowledge_model_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'agent_configs_knowledge_model_id_fkey',
        'agent_configs',
        'models',
        ['knowledge_model_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'agent_configs',
        sa.Column('canvas_label', sa.String(length=200), nullable=True),
    )

    # agents
    op.add_column('agents', sa.Column('llm_model', sa.String(), nullable=True))
