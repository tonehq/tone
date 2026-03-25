import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.upload import Upload
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
        # Deduplicate: if a call log with the same provider_call_id already exists
        # for this agent, return the existing one (prevents duplicates from retries
        # or warm-to-cold worker fallbacks)
        if provider_call_id:
            existing = self.db.query(CallLog).filter(
                CallLog.provider_call_id == provider_call_id,
                CallLog.agent_id == agent_id,
            ).first()
            if existing:
                return existing

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

    def create_upload(
        self,
        r2_object_key: str,
        agent_id: int,
        organization_id: UUID,
        call_log_id: Optional[int] = None,
        file_name: Optional[str] = None,
        content_type: str = "audio/mpeg",
        file_size_bytes: Optional[int] = None,
    ) -> Upload:
        upload = Upload(
            r2_object_key=r2_object_key,
            agent_id=agent_id,
            organization_id=organization_id,
            call_log_id=call_log_id,
            file_name=file_name,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
        )
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        return upload

    def complete_call(
        self,
        call_log_id: int,
        audio_file_path: Optional[str] = None,
        upload_id: Optional[int] = None,
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
        if upload_id:
            call_log.upload_id = upload_id
        call_log.transcript = transcript

        self.db.commit()
        self.db.refresh(call_log)
        return call_log

    def get_upload(self, call_log_id: int) -> Optional[Upload]:
        call_log = self.db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if not call_log or not call_log.upload_id:
            return None
        return self.db.query(Upload).filter(
            Upload.id == call_log.upload_id
        ).first()

    def fail_call(self, call_log_id: int) -> Optional[CallLog]:
        call_log = self.db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if not call_log:
            return None

        call_log.status = "failed"
        call_log.ended_at = int(time.time())
        self.db.commit()
        return call_log
