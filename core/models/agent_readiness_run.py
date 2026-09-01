"""Agent readiness runs — the single table for both current state and history.

One append-only row per persisted readiness run. Replaces the former two-table
design (``agent_readiness_snapshots`` latest-only + ``agent_readiness_events``
history): a run is never overwritten, so "latest" is simply the most recent row
for an ``(agent, config, depth)`` and "history" is the full set of rows. The
indexes below cover both access patterns — the latest/fast-path lookup and the
per-agent history feed.

Columns live in :class:`ReadinessRowMixin` (shared, single source of truth).
"""

from sqlalchemy import Index

from core.models.agent_readiness_common import ReadinessRowMixin
from core.models.base import OrgScopedModel


class AgentReadinessRun(OrgScopedModel, ReadinessRowMixin):
    __tablename__ = "agent_readiness_runs"
    __table_args__ = (
        # Latest-per-agent badge lookup + the edit-based fast-path both key on
        # (agent, …) newest-first; ``computed_at`` in the index lets Postgres
        # satisfy the DISTINCT ON / ORDER BY without a sort.
        Index(
            "ix_readiness_runs_agent_time",
            "agent_id", "computed_at",
        ),
        # Fast-path freshness lookup: newest run for one (agent, config, depth).
        Index(
            "ix_readiness_runs_agent_config_depth_time",
            "agent_id", "config_id", "depth", "computed_at",
        ),
        # List-badge batch fetch (per org) and org-wide audit / drift feed.
        Index(
            "ix_readiness_runs_org_agent",
            "organization_id", "agent_id",
        ),
        Index(
            "ix_readiness_runs_org_time",
            "organization_id", "computed_at",
        ),
        Index(
            "ix_readiness_runs_org_status",
            "organization_id", "overall_status",
        ),
    )
