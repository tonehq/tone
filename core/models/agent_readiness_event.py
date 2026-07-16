"""Append-only readiness event log — one row per readiness run.

Written alongside the snapshot in the same transaction so the two can never
disagree. Powers audit trails, drift trends, and "when did this start
failing?" queries. Not read on any hot path in v1; ready for a follow-up
cron to prune rows older than 90 days when the table grows.
"""

from sqlalchemy import Index

from core.models.agent_readiness_common import ReadinessRowMixin
from core.models.base import OrgScopedModel


class AgentReadinessEvent(OrgScopedModel, ReadinessRowMixin):
    __tablename__ = "agent_readiness_events"
    __table_args__ = (
        # "Latest N runs for one agent" — the primary history query shape.
        Index(
            "ix_readiness_events_agent_time",
            "agent_id", "computed_at",
        ),
        # Org-wide audit / drift feed.
        Index(
            "ix_readiness_events_org_time",
            "organization_id", "computed_at",
        ),
    )
