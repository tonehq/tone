from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from core.models.agent import Agent
from core.models.call import Call
from core.services.base import BaseService

# Bound "active" to a recent window so a single stuck row (crash, missed
# hangup event) can't inflate the metric forever. Anything older than this
# with a NULL ended_at is treated as orphaned, not in-flight.
ACTIVE_CALL_WINDOW = timedelta(hours=1)


class DashboardService(BaseService):
    """Aggregate per-org metrics for the home dashboard.

    Uses the v2 ``calls`` table (no ``status`` column):
      - "active"     = started within ``ACTIVE_CALL_WINDOW`` and not yet ended
      - "successful" = ended with non-zero duration

    NOTE: the live voice pipeline does not yet write to ``calls``; these
    metrics will report 0 until the pipeline cut-over lands.
    """

    def get_stats(self) -> dict:
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        active_since = now - ACTIVE_CALL_WINDOW

        total_agents = (
            self.query(Agent).filter(Agent.deleted_at.is_(None)).count()
        )

        # Count via with_entities(count(id)) instead of Query.count(): the latter
        # wraps a "SELECT <all Call columns>" subquery, which references model
        # columns that may not exist on the live `calls` table (e.g.
        # pipeline_config). Selecting only count(id) keeps tenant scoping while
        # touching a single, guaranteed column.
        active_calls = (
            self.query(Call)
            .with_entities(func.count(Call.id))
            .filter(Call.ended_at.is_(None), Call.started_at >= active_since)
            .scalar()
            or 0
        )

        total_seconds = (
            self.query(Call)
            .with_entities(func.coalesce(func.sum(Call.duration_seconds), 0))
            .filter(Call.started_at >= start_of_month)
            .scalar()
        )
        minutes_used = round(total_seconds / 60, 1)

        finished_calls_30d = (
            self.query(Call)
            .with_entities(func.count(Call.id))
            .filter(
                Call.started_at >= thirty_days_ago,
                Call.ended_at.isnot(None),
            )
            .scalar()
            or 0
        )
        if finished_calls_30d > 0:
            successful_calls_30d = (
                self.query(Call)
                .with_entities(func.count(Call.id))
                .filter(
                    Call.started_at >= thirty_days_ago,
                    Call.ended_at.isnot(None),
                    Call.duration_seconds > 0,
                )
                .scalar()
                or 0
            )
            success_rate = round((successful_calls_30d / finished_calls_30d) * 100, 1)
        else:
            success_rate = 0.0

        return {
            "total_agents": total_agents,
            "active_calls": active_calls,
            "minutes_used": minutes_used,
            "success_rate": success_rate,
        }
