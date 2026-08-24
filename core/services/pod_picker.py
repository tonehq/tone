from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func

from core.models.call import Call
from core.models.pod import Pod
from core.services.base import BaseService
from shared.config import settings

_POD_ALIVE_SECONDS = 180


class PodPicker(BaseService):
    def __init__(self, db, host: Optional[str] = None, prefix: Optional[str] = None):
        super().__init__(db)
        self.host = host or settings.CALL_SERVER_HOST
        # Which voice-pod pool to pick from. Default = the inbound call-worker pool (Twilio media
        # pinning, unchanged). Pass the outbound prefix to pick a WS-bridge hand-off target.
        self.prefix = prefix or settings.CALL_WORKER_PREFIX

    @classmethod
    def for_outbound(cls, db):
        """PodPicker over the dedicated outbound voice-pod pool (WS-bridge hand-off)."""
        return cls(db, prefix=settings.OUTBOUND_CALL_WORKER_PREFIX)

    def _candidate_pods(self):
        prefix = self.prefix
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=_POD_ALIVE_SECONDS)
        return (
            self.db.query(Pod)
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

    def pick(self) -> Optional[Pod]:
        candidates = self._candidate_pods()
        if not candidates:
            return None

        def headroom(pod):
            if (
                pod.mem_limit_mb
                and pod.mem_used_mb is not None
                and pod.cpu_limit_cores
                and pod.cpu_used_cores is not None
            ):
                free_mem = (pod.mem_limit_mb - pod.mem_used_mb) / pod.mem_limit_mb
                free_cpu = (pod.cpu_limit_cores - pod.cpu_used_cores) / pod.cpu_limit_cores
                return min(free_mem, free_cpu)
            return None

        scored = [(headroom(pod), pod) for pod in candidates]
        with_data = [(score, pod) for score, pod in scored if score is not None]
        if with_data:
            best = max(score for score, _ in with_data)
            return next(pod for score, pod in with_data if score == best)

        active = self._active_calls_by_pod()
        return min(candidates, key=lambda pod: active.get(pod.id, 0))

    def url_for(self, pod: Optional[Pod]) -> Optional[str]:
        if pod is None or pod.ordinal is None or not self.host:
            return None
        return f"wss://{self.host}/pod/{pod.ordinal}/ws"

    def http_base_for(self, pod: Optional[Pod]) -> Optional[str]:
        if pod is None or pod.ordinal is None or not self.host:
            return None
        return f"https://{self.host}/pod/{pod.ordinal}"

    def get_pod(self) -> Optional[str]:
        return self.url_for(self.pick())

    def internal_base_for(self, pod: Optional[Pod]) -> Optional[str]:
        """Intra-cluster HTTP base for a specific outbound voice pod, via the StatefulSet's
        headless service (stable per-pod DNS) — e.g.
        ``http://staging-tone-outbound-call-worker-0.staging-tone-outbound-call-headless.staging.svc:8080``.
        Used by the originator to hand a WS bridge off to the picked pod (no ingress involved)."""
        if pod is None or not pod.name:
            return None
        svc = settings.OUTBOUND_CALL_HEADLESS_SERVICE
        ns = settings.POD_SYNC_NAMESPACE
        port = settings.OUTBOUND_CALL_WORKER_PORT
        if not svc or not ns:
            return None
        return f"http://{pod.name}.{svc}.{ns}.svc:{port}"
