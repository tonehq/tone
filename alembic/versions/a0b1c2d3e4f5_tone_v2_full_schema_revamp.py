"""Tone v2 — full schema revamp (23 tables)

Drop all legacy tables and recreate with UUID primary keys,
DateTime timestamps, and org_id as plain UUID (not FK).

Revision ID: a0b1c2d3e4f5
Revises: 17160d116550
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a0b1c2d3e4f5'
down_revision = '17160d116550'
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Old tables to drop (order matters: children before parents)
# ---------------------------------------------------------------------------
OLD_TABLES = [
    # junction / leaf tables first
    "agent_mcp_servers",
    "agent_tools",
    "agent_channels",
    "agent_channel_phone_numbers",
    "channel_phone_numbers",
    "document_chunks",
    "documents",
    "model_instance",
    "model_menu",
    "model_providers_menu",
    "hosting_providers",
    "voices",
    "models",
    "api_keys",
    "accounts",
    "mcp_servers",
    "tools",
    "oauth_connections",
    "call_logs",
    "uploads",
    "agent_configs",
    "agents",
    "channels",
    "generated_api_keys",
    "email_verifications",
    "password_resets",
    "organization_access_requests",
    "organization_invites",
    "members",
    "service_providers",
    "organizations",
    "users",
]

# Old enum types to clean up
OLD_ENUMS = [
    "userstatus",
    "organizationstatus",
    "role",
    "invitestatus",
    "accessrequeststatus",
    "authprovider",
    "agenttype",
    "channeltype",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Drop all old tables (ignore if not exists for safety)
    # ------------------------------------------------------------------
    for table in OLD_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

    # Drop old enum types
    for enum_name in OLD_ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")

    # ------------------------------------------------------------------
    # 2. Create new tables — Global Catalog
    # ------------------------------------------------------------------

    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    # model_providers
    op.create_table(
        "model_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(50), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("website_url", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider_id", name="uq_model_providers_provider_id"),
    )

    # models
    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("sample_id", sa.String(500), nullable=True),
        sa.Column("sample_list", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider_id", "name", name="uq_models_provider_name"),
    )

    # model_voices
    op.create_table(
        "model_voices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accent", sa.String(120), nullable=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("gender", sa.String(200), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("language_list", postgresql.JSONB(), nullable=True),
        sa.Column("sample_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # model_languages
    op.create_table(
        "model_languages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ------------------------------------------------------------------
    # 3. Identity (users + membership)
    # ------------------------------------------------------------------

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(248), nullable=True),
        sa.Column("encrypted_password", sa.String(255), nullable=True),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("default_organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # email_requests
    op.create_table(
        "email_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("template_context", postgresql.JSONB(), nullable=True),
        sa.Column("delivery_status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("token_hash", sa.String(255), nullable=True, unique=True),
        sa.Column("created_by_user_id", sa.String(50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # invites
    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("email_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("email_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "email", name="uq_invites_org_email"),
    )

    # members
    op.create_table(
        "members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'member'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_members_org_user"),
    )

    # ------------------------------------------------------------------
    # 4. Auth & Credentials
    # ------------------------------------------------------------------

    # oauth_connections
    op.create_table(
        "oauth_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("provider_slug", sa.String(80), nullable=False),
        sa.Column("label", sa.String(80), nullable=True),
        sa.Column("auth_type", sa.String(30), nullable=False),
        sa.Column("encrypted_credentials", postgresql.JSONB(), nullable=True),
        sa.Column("public_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_providers.id"), nullable=False),
        sa.Column("label", sa.String(80), nullable=True),
        sa.Column("encrypted_key", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "provider_id", "label", name="uq_api_keys_org_provider_label"),
    )

    # ------------------------------------------------------------------
    # 5. Telephony
    # ------------------------------------------------------------------

    # channels
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("encrypted_config", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_channels_org_name"),
    )

    # ------------------------------------------------------------------
    # 6. Uploads
    # ------------------------------------------------------------------

    # uploads
    op.create_table(
        "uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("container_name", sa.String(120), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ------------------------------------------------------------------
    # 7. Agent Core
    # ------------------------------------------------------------------

    # agents (created before agent_configs due to circular FK — use use_alter)
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("agent_type", sa.String(20), nullable=False),
        sa.Column("llm_model", sa.String(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_agents_org_name"),
    )

    # agent_configs
    op.create_table(
        "agent_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("canvas_label", sa.String(200), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_message", sa.String(1000), nullable=True),
        sa.Column("system_prompt_template", sa.Text(), nullable=True),
        sa.Column("conversation_history_token_limit", sa.Integer(), nullable=True),
        sa.Column("language_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_languages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("knowledge_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("voice_settings", postgresql.JSONB(), nullable=True),
        sa.Column("stt_settings", postgresql.JSONB(), nullable=True),
        sa.Column("conversation_settings", postgresql.JSONB(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_configs_agent_version"),
    )

    # Add the deferred published_config_id column + FK now that agent_configs exists
    op.add_column("agents", sa.Column("published_config_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_agents_published_config_id",
        "agents",
        "agent_configs",
        ["published_config_id"],
        ["id"],
        ondelete="SET NULL",
    )


    # phone_numbers (depends on channels + agents)
    op.create_table(
        "phone_numbers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "number", name="uq_phone_numbers_org_number"),
    )

    # ------------------------------------------------------------------
    # 8. Bound Resources
    # ------------------------------------------------------------------

    # mcp_servers
    op.create_table(
        "mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("server_url", sa.String(500), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=True),
        sa.Column("icon", sa.String(255), nullable=True),
        sa.Column("oauth_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_mcp_servers_org_name"),
    )

    # tools
    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tool_type", sa.String(80), nullable=False),
        sa.Column("action_params_schema", postgresql.JSONB(), nullable=True),
        sa.Column("trigger_phrases", postgresql.JSONB(), nullable=True),
        sa.Column("entity", postgresql.JSONB(), nullable=True),
        sa.Column("oauth_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_tools_org_name"),
    )

    # ------------------------------------------------------------------
    # 9. Config Bindings (agent_knowledge_bases, agent_mcp_servers, agent_tools)
    # ------------------------------------------------------------------

    # agent_knowledge_bases
    op.create_table(
        "agent_knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_config_id", "upload_id", name="uq_agent_kb_config_upload"),
    )

    # agent_mcp_servers
    op.create_table(
        "agent_mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mcp_server_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("oauth_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_config_id", "mcp_server_id", name="uq_agent_mcp_config_server"),
    )

    # agent_tools
    op.create_table(
        "agent_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_config_id", "tool_id", name="uq_agent_tools_config_tool"),
    )

    # ------------------------------------------------------------------
    # 10. Calls & Metrics
    # ------------------------------------------------------------------

    # calls
    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("from_phone_number_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_phone_number_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_number_raw_by_provider", sa.String(50), nullable=True),
        sa.Column("provider_call_id", sa.String(120), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("recording_upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recording_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("webhook_type", sa.String(50), nullable=False),
        sa.Column("trigger_events", sa.String(200), nullable=True),
        sa.Column("endpoint_url", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    """Downgrade is destructive — drops all v2 tables.
    Restoring v1 schema requires replaying all prior migrations from scratch."""

    v2_tables = [
        "webhooks",
        "calls",
        "agent_tools",
        "agent_mcp_servers",
        "agent_knowledge_bases",
        "tools",
        "mcp_servers",
        "phone_numbers",
        "agent_configs",
        "agents",
        "uploads",
        "channels",
        "api_keys",
        "oauth_connections",
        "members",
        "invites",
        "email_requests",
        "users",
        "model_languages",
        "model_voices",
        "models",
        "model_providers",
        "organizations",
    ]
    for table in v2_tables:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
