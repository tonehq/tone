import json
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from core.models.agent import Agent
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

    def get_filter_values(self, column_name: str) -> Dict[str, Any]:
        allowed = {
            "status": CallLog.status,
            "transport_type": CallLog.transport_type,
            "from_number": CallLog.from_number,
            "to_number": CallLog.to_number,
            "agent_name": None,
            "agent_type": None,
        }

        if column_name not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column: {column_name}. Allowed: {', '.join(sorted(allowed.keys()))}",
            )

        base = self.query(CallLog).join(Agent, CallLog.agent_id == Agent.id)

        if column_name == "agent_name":
            rows = base.with_entities(Agent.name).distinct().all()
            values = sorted([r[0] for r in rows if r[0] is not None])
        elif column_name == "agent_type":
            rows = base.with_entities(Agent.agent_type).distinct().all()
            values = sorted([r[0].name for r in rows if r[0] is not None])
        else:
            col = allowed[column_name]
            rows = base.with_entities(col).distinct().all()
            values = sorted([r[0] for r in rows if r[0] is not None])

        return {"column": column_name, "values": values}

    def get_call_logs(
        self,
        page_no: int = 1,
        page_size: int = 10,
        start_date_time: Optional[int] = None,
        end_date_time: Optional[int] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        base_query = (
            self.query(CallLog)
            .join(Agent, CallLog.agent_id == Agent.id)
        )

        if start_date_time is not None:
            base_query = base_query.filter(CallLog.started_at >= start_date_time)
        if end_date_time is not None:
            base_query = base_query.filter(CallLog.started_at <= end_date_time)

        allowed_fields = {
            "status", "transport_type", "from_number", "to_number",
            "duration_seconds", "started_at", "ended_at",
            "agent_name", "agent_type",
        }

        if filters:
            for f in filters:
                field = f.get("field")
                operator = f.get("operator")
                value = f.get("value")

                if field not in allowed_fields:
                    continue

                if field == "agent_name":
                    col = Agent.name
                elif field == "agent_type":
                    col = Agent.agent_type
                elif not hasattr(CallLog, field):
                    continue
                else:
                    col = getattr(CallLog, field)

                if operator == "equal_to":
                    base_query = base_query.filter(col == value)
                elif operator == "greater_than":
                    base_query = base_query.filter(col > value)
                elif operator == "less_than":
                    base_query = base_query.filter(col < value)
                elif operator == "between":
                    if isinstance(value, list) and len(value) == 2:
                        base_query = base_query.filter(col.between(value[0], value[1]))
                elif operator == "in":
                    if isinstance(value, list):
                        base_query = base_query.filter(col.in_(value))
                elif operator == "contains":
                    base_query = base_query.filter(col.ilike(f"%{value}%"))

        total = base_query.count()

        sort_col = getattr(CallLog, sort_by, None) if sort_by and sort_by in allowed_fields else CallLog.started_at
        order_fn = asc if sort_order == "asc" else desc
        base_query = base_query.order_by(order_fn(sort_col))

        offset = (page_no - 1) * page_size
        results = (
            base_query
            .add_columns(Agent.name.label("agent_name"), Agent.agent_type.label("agent_type"))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        data = []
        for row in results:
            call_log = row[0]
            agent_name = row[1]
            agent_type = row[2]

            data.append({
                "id": call_log.id,
                "uuid": str(call_log.uuid),
                "agent_id": call_log.agent_id,
                "agent_name": agent_name,
                "agent_type": agent_type.name if agent_type else None,
                "started_at": call_log.started_at,
                "ended_at": call_log.ended_at,
                "duration_seconds": call_log.duration_seconds,
                "transcript": call_log.transcript,
                "from_number": call_log.from_number,
                "to_number": call_log.to_number,
                "transport_type": call_log.transport_type,
                "status": call_log.status,
                "audio_file_path": call_log.audio_file_path,
                "provider_call_id": call_log.provider_call_id,
            })

        return {
            "data": data,
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def get_call_log_by_id(self, call_log_id: int) -> Optional[Dict[str, Any]]:
        result = (
            self.query(CallLog)
            .join(Agent, CallLog.agent_id == Agent.id)
            .add_columns(Agent.name.label("agent_name"), Agent.agent_type.label("agent_type"))
            .filter(CallLog.id == call_log_id)
            .first()
        )

        if not result:
            return None

        call_log = result[0]
        agent_name = result[1]
        agent_type = result[2]

        return {
            "id": call_log.id,
            "uuid": str(call_log.uuid),
            "agent_id": call_log.agent_id,
            "agent_name": agent_name,
            "agent_type": agent_type.name if agent_type else None,
            "started_at": call_log.started_at,
            "ended_at": call_log.ended_at,
            "duration_seconds": call_log.duration_seconds,
            "transcript": call_log.transcript,
            "from_number": call_log.from_number,
            "to_number": call_log.to_number,
            "transport_type": call_log.transport_type,
            "status": call_log.status,
            "audio_file_path": call_log.audio_file_path,
            "provider_call_id": call_log.provider_call_id,
        }
