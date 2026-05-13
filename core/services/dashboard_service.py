import time
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.call_log import CallLog
from core.services.base import BaseService


class DashboardService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    def get_stats(self) -> dict:
        total_agents = self.query(Agent).count()

        active_calls = (
            self.query(CallLog)
            .filter(CallLog.status == "in_progress")
            .count()
        )

        # Minutes used this month
        now = datetime.now(timezone.utc)
        start_of_month = int(
            datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp()
        )
        total_seconds = (
            self.query(CallLog)
            .with_entities(func.coalesce(func.sum(CallLog.duration_seconds), 0))
            .filter(CallLog.started_at >= start_of_month)
            .scalar()
        )
        minutes_used = round(total_seconds / 60, 1)

        # Success rate over last 30 days
        thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
        total_calls_30d = (
            self.query(CallLog)
            .filter(CallLog.started_at >= thirty_days_ago)
            .count()
        )
        if total_calls_30d > 0:
            completed_calls_30d = (
                self.query(CallLog)
                .filter(
                    CallLog.started_at >= thirty_days_ago,
                    CallLog.status == "completed",
                )
                .count()
            )
            success_rate = round((completed_calls_30d / total_calls_30d) * 100, 1)
        else:
            success_rate = 0

        return {
            "total_agents": total_agents,
            "active_calls": active_calls,
            "minutes_used": minutes_used,
            "success_rate": success_rate,
        }
