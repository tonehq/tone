import time
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.call_log import CallLog
from core.services.base import BaseService


class CallLogService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    def create_call_log(
        self,
        agent_id: int,
        organization_id: UUID,
        provider_call_id: Optional[str] = None,
        transport_type: Optional[str] = None,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
    ) -> CallLog:
        call_log = CallLog(
            agent_id=agent_id,
            organization_id=organization_id,
            provider_call_id=provider_call_id,
            transport_type=transport_type,
            from_number=from_number,
            to_number=to_number,
            status="in_progress",
            started_at=int(time.time()),
        )
        self.db.add(call_log)
        self.db.commit()
        self.db.refresh(call_log)
        return call_log

    def complete_call(
        self,
        call_log_id: int,
        audio_file_path: Optional[str] = None,
        transcript: Optional[List[dict]] = None,
    ) -> Optional[CallLog]:
        call_log = self.db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if not call_log:
            return None

        now = int(time.time())
        call_log.status = "completed"
        call_log.ended_at = now
        call_log.duration_seconds = now - call_log.started_at
        call_log.audio_file_path = audio_file_path
        call_log.transcript = transcript

        self.db.commit()
        self.db.refresh(call_log)
        return call_log

    def fail_call(self, call_log_id: int) -> Optional[CallLog]:
        call_log = self.db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if not call_log:
            return None

        call_log.status = "failed"
        call_log.ended_at = int(time.time())
        self.db.commit()
        return call_log
