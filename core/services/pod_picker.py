from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from core.models.call import Call
from core.models.pod import Pod
from core.services.base import BaseService
from shared.config import settings

_POD_ALIVE_SECONDS = 180


class PodPicker(BaseService):
    def __init__(self, db, host: Optional[str] = None):
        super().__init__(db)
        self.host = host or settings.CALL_SERVER_HOST

    def _candidate_pods(self):
        prefix = settings.CALL_WORKER_PREFIX
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=_POD_ALIVE_SECONDS)
        return (
            self.db.query(Pod)
            .options(joinedload(Pod.node))
            .filter(
                Pod.name.like(f"{prefix}-%"),
                Pod.ordinal.isnot(None),
                Pod.last_seen_at.isnot(None),
                Pod.last_seen_at >= cutoff,
            )
            .all()
        )

    def _active_calls_by_pod(self):
        rows = (
            self.db.query(Call.pod_id, func.count(Call.id))
            .filter(Call.ended_at.is_(None), Call.pod_id.isnot(None))
            .group_by(Call.pod_id)
            .all()
        )
        return {pod_id: count for pod_id, count in rows}

    def _pick(self) -> Optional[Pod]:
        candidates = self._candidate_pods()
        if not candidates:
            return None

        active = self._active_calls_by_pod()

        def node_freeness(pod):
            node = pod.node
            if node is None or node.vcpu_per_pod is None:
                return (float("-inf"), float("-inf"))
            return (node.vcpu_per_pod, node.ram_per_pod_mb or 0.0)

        best = max(node_freeness(p) for p in candidates)
        if best[0] != float("-inf"):
            pool = [p for p in candidates if node_freeness(p) == best]
        else:
            pool = candidates

        return min(pool, key=lambda p: active.get(p.id, 0))

    def get_pod(self) -> Optional[str]:
        pod = self._pick()
        if pod is None or pod.ordinal is None or not self.host:
            return None
        return f"wss://{self.host}/pod/{pod.ordinal}/ws"
