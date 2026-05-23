from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from core.models.agent import Agent
from core.models.call import Call
from core.services.base import BaseService


class DashboardService(BaseService):
    """Aggregate per-org metrics for the home dashboard. Uses the v2 ``calls``
    table (no ``status`` column) — "active" = call not yet ended, "successful"
    = call ended with non-zero duration."""

    def get_stats(self) -> dict:
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        total_agents = (
            self.query(Agent).filter(Agent.deleted_at.is_(None)).count()
        )

        active_calls = self.query(Call).filter(Call.ended_at.is_(None)).count()

        total_seconds = (
            self.query(Call)
            .with_entities(func.coalesce(func.sum(Call.duration_seconds), 0))
            .filter(Call.started_at >= start_of_month)
            .scalar()
            or 0
        )
        minutes_used = round(int(total_seconds) / 60, 1)

        total_calls_30d = (
            self.query(Call).filter(Call.started_at >= thirty_days_ago).count()
        )
        if total_calls_30d > 0:
            completed_calls_30d = (
                self.query(Call)
                .filter(
                    Call.started_at >= thirty_days_ago,
                    Call.ended_at.isnot(None),
                    Call.duration_seconds > 0,
                )
                .count()
            )
            success_rate = round((completed_calls_30d / total_calls_30d) * 100, 1)
        else:
            success_rate = 0.0

        return {
            "total_agents": total_agents,
            "active_calls": active_calls,
            "minutes_used": minutes_used,
            "success_rate": success_rate,
        }
