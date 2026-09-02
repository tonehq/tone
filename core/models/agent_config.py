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
        # ``mode`` may only be the two conversation-flow drivers the API accepts
        # (request schema is ``Literal["prompt", "workflow"]``). This mirrors that
        # enforcement at the DB level so no path can persist an out-of-set value.
        CheckConstraint(
            "mode IN ('prompt', 'workflow')",
            name="ck_agent_configs_mode_valid",
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

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "version": self.version,
            "canvas_label": self.canvas_label,
            "mode": self.mode,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "is_default": self.is_default,
            "is_template": self.is_template,
            "name": self.name,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "first_message": self.first_message,
            "end_call_message": self.end_call_message,
            "system_prompt_template": self.system_prompt_template,
            "conversation_history_token_limit": self.conversation_history_token_limit,
            "language_id": str(self.language_id) if self.language_id else None,
            "knowledge_model_id": str(self.knowledge_model_id) if self.knowledge_model_id else None,
            "llm_settings": self.llm_settings,
            "voice_settings": self.voice_settings,
            "stt_settings": self.stt_settings,
            "conversation_settings": self.conversation_settings,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
