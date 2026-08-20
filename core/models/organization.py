import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import false as sa_false

from core.database.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(512), nullable=True)
    website = Column(String(512), nullable=True)

    subscription_tier = Column(String(50), nullable=False, default="free")
    status = Column(String(50), nullable=False, default="active")
    max_agents = Column(Integer, nullable=False, default=5)
    max_test_runs_per_month = Column(Integer, nullable=False, default=100)
    max_production_calls_per_month = Column(Integer, nullable=False, default=1000)
    max_users = Column(Integer, nullable=False, default=5)

    sso_enabled = Column(Boolean, nullable=False, default=False)
    sso_provider = Column(String(50), nullable=True)
    sso_config = Column(JSONB, nullable=True)
    settings = Column(JSONB, nullable=True, default=dict)
    # Per-org RAG-eval knobs (auto-run flag, judge/answer/generation models,
    # top_k, thresholds, enabled metrics). NULL / missing keys → env fallback
    # via ``core.services.org_settings.get_eval_settings``.
    eval_settings = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)

    # Per-org log level (TRACE/DEBUG/INFO/…). NULL = inherit the env baseline.
    # An agent's own log_level overrides this. See core/services/log_level_resolver.py.
    log_level = Column(String(20), nullable=True)

    industry = Column(String(100), nullable=True)
    use_case = Column(String(100), nullable=True)
    onboarding_completed = Column(Boolean, nullable=False, default=False, server_default=sa_false())

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "logo_url": self.logo_url,
            "website": self.website,
            "subscription_tier": self.subscription_tier,
            "status": self.status,
            "max_agents": self.max_agents,
            "max_test_runs_per_month": self.max_test_runs_per_month,
            "max_production_calls_per_month": self.max_production_calls_per_month,
            "max_users": self.max_users,
            "sso_enabled": self.sso_enabled,
            "industry": self.industry,
            "use_case": self.use_case,
            "onboarding_completed": self.onboarding_completed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
