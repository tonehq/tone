from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, aliased

from core.models.agent import Agent
from core.models.call import Call
from core.models.channel import Channel
from core.models.phone_number import PhoneNumber
from core.models.upload import Upload
from core.services.base import BaseService


class CallService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_filter_values(self, column_name: str) -> Dict[str, Any]:
        allowed = {
            "status": None,
            "direction": Call.direction,
            "agent_name": None,
            "agent_type": None,
            "channel_type": None,
        }

        if column_name not in allowed:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column: {column_name}. Allowed: {', '.join(sorted(allowed.keys()))}",
            )

        base = self.query(Call).join(Agent, Call.agent_id == Agent.id)

        if column_name == "agent_name":
            rows = base.with_entities(Agent.name).distinct().all()
            values = sorted([r[0] for r in rows if r[0] is not None])
        elif column_name == "agent_type":
            rows = base.with_entities(Agent.agent_type).distinct().all()
            values = sorted([r[0] for r in rows if r[0] is not None])
        elif column_name == "channel_type":
            rows = (
                base.join(Channel, Call.channel_id == Channel.id)
                .with_entities(Channel.channel_type)
                .distinct()
                .all()
            )
            values = sorted([r[0] for r in rows if r[0] is not None])
        elif column_name == "status":
            # Status is derived: ended_at IS NOT NULL → completed, else in_progress
            values = ["completed", "in_progress"]
        else:
            col = allowed[column_name]
            rows = base.with_entities(col).distinct().all()
            values = sorted([r[0] for r in rows if r[0] is not None])

        return {"column": column_name, "values": values}

    def get_calls(
        self,
        page_no: int = 1,
        page_size: int = 10,
        start_date_time: Optional[str] = None,
        end_date_time: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        from_pn = aliased(PhoneNumber, name="from_pn")
        to_pn = aliased(PhoneNumber, name="to_pn")

        base_query = (
            self.query(Call)
            .join(Agent, Call.agent_id == Agent.id)
            .join(Channel, Call.channel_id == Channel.id)
            .outerjoin(from_pn, Call.from_phone_number_id == from_pn.id)
            .outerjoin(to_pn, Call.to_phone_number_id == to_pn.id)
        )

        if start_date_time is not None:
            base_query = base_query.filter(Call.started_at >= start_date_time)
        if end_date_time is not None:
            base_query = base_query.filter(Call.started_at <= end_date_time)

        # Column mapping for filters and sorting
        column_map = {
            "status": None,  # derived, handled specially
            "direction": Call.direction,
            "duration_seconds": Call.duration_seconds,
            "started_at": Call.started_at,
            "ended_at": Call.ended_at,
            "agent_name": Agent.name,
            "agent_type": Agent.agent_type,
            "channel_type": Channel.channel_type,
        }

        if filters:
            for f in filters:
                field = f.get("field")
                operator = f.get("operator")
                value = f.get("value")

                if field == "status":
                    # Derived: completed = ended_at IS NOT NULL
                    if operator == "in" and isinstance(value, list):
                        if "completed" in value and "in_progress" not in value:
                            base_query = base_query.filter(Call.ended_at.isnot(None))
                        elif "in_progress" in value and "completed" not in value:
                            base_query = base_query.filter(Call.ended_at.is_(None))
                    continue

                col = column_map.get(field)
                if col is None:
                    continue

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

        # Sorting
        sort_col = column_map.get(sort_by, Call.started_at) if sort_by else Call.started_at
        if sort_col is None:
            sort_col = Call.started_at
        order_fn = asc if sort_order == "asc" else desc
        base_query = base_query.order_by(order_fn(sort_col))

        offset = (page_no - 1) * page_size
        results = (
            base_query
            .add_columns(
                Agent.name.label("agent_name"),
                Agent.agent_type.label("agent_type"),
                Channel.channel_type.label("channel_type"),
                from_pn.number.label("from_number"),
                to_pn.number.label("to_number"),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )

        data = [
            self.call_response(
                call=row[0],
                agent_name=row[1],
                agent_type=row[2],
                channel_type=row[3],
                from_number=row[4],
                to_number=row[5],
            )
            for row in results
        ]

        return {
            "data": data,
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def get_call_by_id(self, call_id: str) -> Optional[Dict[str, Any]]:
        from_pn = aliased(PhoneNumber, name="from_pn")
        to_pn = aliased(PhoneNumber, name="to_pn")

        result = (
            self.query(Call)
            .join(Agent, Call.agent_id == Agent.id)
            .join(Channel, Call.channel_id == Channel.id)
            .outerjoin(from_pn, Call.from_phone_number_id == from_pn.id)
            .outerjoin(to_pn, Call.to_phone_number_id == to_pn.id)
            .add_columns(
                Agent.name.label("agent_name"),
                Agent.agent_type.label("agent_type"),
                Channel.channel_type.label("channel_type"),
                from_pn.number.label("from_number"),
                to_pn.number.label("to_number"),
            )
            .filter(Call.id == call_id)
            .first()
        )

        if not result:
            return None

        return self.call_response(
            call=result[0],
            agent_name=result[1],
            agent_type=result[2],
            channel_type=result[3],
            from_number=result[4],
            to_number=result[5],
        )

    def call_response(
        self,
        call: Call,
        agent_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        channel_type: Optional[str] = None,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        metadata = call.metadata_ or {}
        status = "completed" if call.ended_at else "in_progress"

        return {
            "id": str(call.id),
            "agent_id": str(call.agent_id),
            "agent_name": agent_name,
            "agent_type": agent_type,
            "direction": call.direction,
            "channel_type": channel_type,
            "status": status,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": call.duration_seconds,
            "from_number": from_number or call.from_number_raw_by_provider,
            "to_number": to_number,
            "provider_call_id": call.provider_call_id,
            "recording_upload_id": str(call.recording_upload_id) if call.recording_upload_id else None,
            "transcript": metadata.get("transcript"),
            "metrics": metadata.get("metrics"),
            "tool_calls": metadata.get("tool_calls"),
        }
