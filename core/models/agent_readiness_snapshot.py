"""Latest-state readiness snapshot — one row per (agent, config, depth).

UPSERTed on every readiness run. Powers fast list badges and the edit-based
fast-path in ``ReadinessService.check`` (matching ``dependency_stamp`` means
the row is still valid — no need to re-run).
"""

from sqlalchemy import Index, UniqueConstraint

from core.models.agent_readiness_common import ReadinessRowMixin
from core.models.base import OrgScopedModel


class AgentReadinessSnapshot(OrgScopedModel, ReadinessRowMixin):
    __tablename__ = "agent_readiness_snapshots"
    __table_args__ = (
        # One row per config version per depth. Postgres treats NULLs as
        # distinct, so a config_id=NULL row (brand-new agent) is its own slot
        # per depth — acceptable trade-off for v1.
        UniqueConstraint(
            "agent_id", "config_id", "depth",
            name="uq_readiness_snapshots_agent_config_depth",
        ),
        Index(
            "ix_readiness_snapshots_org_agent",
            "organization_id", "agent_id",
        ),
        Index(
            "ix_readiness_snapshots_org_status",
            "organization_id", "overall_status",
        ),
    )
