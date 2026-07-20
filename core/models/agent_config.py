from sqlalchemy import CheckConstraint, Column, String, Integer, Boolean, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class AgentConfig(OrgScopedModel):
    __tablename__ = "agent_configs"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_configs_agent_version"),
        # A standalone template (seeded from JSON, no source agent) has
        # ``agent_id IS NULL``. Every other row — versions of a live agent,
        # or a template snapshotted from an existing agent — MUST have an
        # agent_id. Enforced in the DB so no code path can produce an
        # orphan non-template row.
        CheckConstraint(
            "is_template = true OR agent_id IS NOT NULL",
            name="ck_agent_configs_agent_required_unless_template",
        ),
    )

    # NULL is only legal when ``is_template = true`` (see CHECK above).
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True)
    version = Column(Integer, nullable=False)
    canvas_label = Column(String(200), nullable=True)
    # Conversation-flow driver: "prompt" (single system prompt) | "workflow" (assigned graph).
    mode = Column(String(16), nullable=False, server_default="prompt")
    # The assigned org-level workflow when mode == "workflow" (SET NULL on workflow delete).
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_default = Column(Boolean, nullable=False, default=False)
    # Marks this config as a reusable template surfaced in the "create from
    # template" picker. ``name`` is the template's display label (nullable for
    # ordinary, non-template config versions).
    is_template = Column(Boolean, nullable=False, server_default="false")
    name = Column(String(200), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    first_message = Column(String(1000), nullable=True)
    end_call_message = Column(String(1000), nullable=True)
    system_prompt_template = Column(Text, nullable=True)
    conversation_history_token_limit = Column(Integer, nullable=True)
    language_id = Column(UUID(as_uuid=True), ForeignKey("model_languages.id", ondelete="SET NULL"), nullable=True)
    knowledge_model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="SET NULL"), nullable=True)
    llm_settings = Column(JSONB, nullable=True)
    voice_settings = Column(JSONB, nullable=True)
    stt_settings = Column(JSONB, nullable=True)
    conversation_settings = Column(JSONB, nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
