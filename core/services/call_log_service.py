from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.call import Call
from core.models.channel import Channel
from core.models.phone_number import PhoneNumber
from core.models.upload import Upload
from core.services.base import BaseService


class CallLogService(BaseService):
    """Adapter that writes to the new ``calls`` table while keeping the same
    interface that ``agent_factory_service`` expects (create_call_log,
    complete_call, fail_call, delete_call, create_upload).
    """

    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_channel_and_phones(self, agent_id, organization_id, from_number, to_number):
        """Resolve channel_id, from_phone_number_id, to_phone_number_id from raw numbers."""
        channel_id = None
        from_pn_id = None
        to_pn_id = None

        if to_number:
            pn = self.db.query(PhoneNumber).filter(PhoneNumber.number == to_number).first()
            if pn:
                to_pn_id = pn.id
                channel_id = pn.channel_id

        if from_number:
            pn = self.db.query(PhoneNumber).filter(PhoneNumber.number == from_number).first()
            if pn:
                from_pn_id = pn.id
                if not channel_id:
                    channel_id = pn.channel_id

        # Fallback: first channel in the org
        if not channel_id:
            ch = self.db.query(Channel).filter(Channel.organization_id == organization_id).first()
            channel_id = ch.id if ch else None

        return channel_id, from_pn_id, to_pn_id

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_call_log(
        self,
        agent_id,
        organization_id: UUID,
        provider_call_id: Optional[str] = None,
        transport_type: Optional[str] = None,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Call:
        # Deduplicate
        if provider_call_id:
            existing = (
                self.db.query(Call)
                .filter(
                    Call.provider_call_id == provider_call_id,
                    Call.agent_id == agent_id,
                )
                .first()
            )
            if existing:
                return existing

        channel_id, from_pn_id, to_pn_id = self._resolve_channel_and_phones(
            agent_id, organization_id, from_number, to_number,
        )
        if not channel_id:
            logger.warning("No channel found for agent_id={}, cannot create call record", agent_id)
            return None

        direction = "outbound" if transport_type == "outbound" else "inbound"

        call = Call(
            agent_id=agent_id,
            organization_id=organization_id,
            channel_id=channel_id,
            direction=direction,
            provider_call_id=provider_call_id,
            trace_id=trace_id,
            from_phone_number_id=from_pn_id,
            to_phone_number_id=to_pn_id,
            from_number_raw_by_provider=from_number,
            started_at=datetime.now(timezone.utc),
            metadata_={},
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def create_upload(
        self,
        r2_object_key: str,
        agent_id,
        organization_id: UUID,
        call_log_id=None,
        file_name: Optional[str] = None,
        content_type: str = "audio/mpeg",
        file_size_bytes: Optional[int] = None,
    ) -> Upload:
        upload = Upload(
            organization_id=organization_id,
            container_name="call-recordings",
            file_path=r2_object_key,
            file_name=file_name,
            file_type=content_type,
            size_bytes=file_size_bytes,
            purpose="recording",
            status="ready",
            meta_data={"agent_id": str(agent_id), "call_id": str(call_log_id)} if call_log_id else {"agent_id": str(agent_id)},
        )
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        return upload

    # ------------------------------------------------------------------
    # Complete / Fail / Delete
    # ------------------------------------------------------------------

    def complete_call(
        self,
        call_log_id,
        audio_file_path: Optional[str] = None,
        upload_id=None,
        transcript: Optional[List[dict]] = None,
        metrics: Optional[dict] = None,
        tool_calls: Optional[List[dict]] = None,
    ) -> Optional[Call]:
        call = self.db.query(Call).filter(Call.id == call_log_id).first()
        if not call:
            return None

        now = datetime.now(timezone.utc)
        call.ended_at = now
        if call.started_at:
            call.duration_seconds = int((now - call.started_at).total_seconds())

        if upload_id:
            call.recording_upload_id = upload_id

        # Store transcript, tool_calls, audio_file_path in metadata JSONB.
        # Metrics live in their own table (call_metrics) — see CallMetricsService.
        metadata = call.metadata_ or {}
        if transcript:
            metadata["transcript"] = transcript
        if tool_calls:
            metadata["tool_calls"] = tool_calls
        if audio_file_path:
            metadata["audio_file_path"] = audio_file_path
        call.metadata_ = metadata

        self.db.commit()
        self.db.refresh(call)

        if metrics:
            try:
                from core.services.call_metrics_service import CallMetricsService
                CallMetricsService(self.db, org_id=call.organization_id).upsert_for_call(
                    call.id, call.organization_id, metrics
                )
            except Exception as e:
                logger.error("Failed to persist call_metrics for call {}: {}", call.id, e)

        # Additionally persist each tool/MCP invocation as a queryable row.
        # Wrapped so a persistence failure never breaks call completion.
        if tool_calls:
            try:
                from core.services.tool_execution_service import ToolExecutionService
                count = ToolExecutionService(
                    self.db, org_id=call.organization_id
                ).record_executions(call.id, call.agent_id, tool_calls)
                logger.info("Persisted {} tool_executions for call {}", count, call.id)
            except Exception as e:
                logger.error("Failed to persist tool_executions for call {}: {}", call.id, e)

        return call

    def fail_call(self, call_log_id) -> Optional[Call]:
        call = self.db.query(Call).filter(Call.id == call_log_id).first()
        if not call:
            return None

        call.ended_at = datetime.now(timezone.utc)
        metadata = call.metadata_ or {}
        metadata["status"] = "failed"
        call.metadata_ = metadata

        self.db.commit()
        return call

    def delete_call(self, call_log_id) -> None:
        call = self.db.query(Call).filter(Call.id == call_log_id).first()
        if call:
            self.db.delete(call)
            self.db.commit()
