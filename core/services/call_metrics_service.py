from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import asc, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.call import Call
from core.models.call_metrics import CallMetrics
from core.services.base import BaseService

# Single source of truth for the metric columns. Drives the upsert payload,
# the ON CONFLICT update set, and the response formatter — change a column
# here and all three stay in sync.
_METRIC_FIELDS = (
    "ttfb",
    "processing",
    "llm_usage",
    "tts_usage",
    "stt_usage",
    "user_bot_latency",
    "turns",
    "turn_metrics",
)


class CallMetricsService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_for_call(
        self,
        call_id: UUID,
        organization_id: UUID,
        metrics: Dict[str, Any],
    ) -> None:
        """Insert or update the call_metrics row for a given call_id.

        Called from CallLogService.complete_call after the pipeline assembles
        the metrics dict. Idempotent on call_id (UNIQUE).

        ``organization_id`` is passed in by the caller (which already has the
        loaded ``Call``) so we avoid a redundant SELECT and the race window
        that opens between the lookup and the INSERT.
        """
        payload = {
            "organization_id": organization_id,
            "call_id": call_id,
            "updated_at": datetime.now(timezone.utc),
            **{field: metrics.get(field) for field in _METRIC_FIELDS},
        }

        stmt = pg_insert(CallMetrics).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["call_id"],
            set_={
                **{field: getattr(stmt.excluded, field) for field in _METRIC_FIELDS},
                "updated_at": stmt.excluded.updated_at,
            },
        )
        self.db.execute(stmt)
        self.db.commit()

    # ------------------------------------------------------------------
    # Read — list with filter/sort/pagination (mirrors CallService.get_calls)
    # ------------------------------------------------------------------

    # Whitelisted filter/sort fields → SQLAlchemy column. Anything not listed
    # here is rejected, which means we never order or filter by user input.
    _COLUMN_MAP = {
        "agent_name": Agent.name,
        "agent_type": Agent.agent_type,
        "started_at": Call.started_at,
        "ended_at": Call.ended_at,
        "duration_seconds": Call.duration_seconds,
        # Used by the "show metrics for this call" deep-link from Call History.
        "call_id": CallMetrics.call_id,
        # JSONB snapshot of LLM/STT/TTS used to serve the call.
        "llm_provider": Call.pipeline_config["llm"]["provider_name"].astext,
        "llm_model": Call.pipeline_config["llm"]["model_name"].astext,
        "stt_provider": Call.pipeline_config["stt"]["provider_name"].astext,
        "stt_model": Call.pipeline_config["stt"]["model_name"].astext,
        "tts_provider": Call.pipeline_config["tts"]["provider_name"].astext,
        "tts_model": Call.pipeline_config["tts"]["model_name"].astext,
    }

    def _base_query(self):
        """Query joined to Call + Agent with the extra columns the formatter needs.

        Shared by ``list_metrics`` and ``get_by_call_id`` so both endpoints return
        the same shape from the same source.
        """
        return (
            self.query(CallMetrics)
            .join(Call, CallMetrics.call_id == Call.id)
            .join(Agent, Call.agent_id == Agent.id)
            .add_columns(
                Call.id.label("call_id_col"),
                Call.agent_id.label("agent_id_col"),
                Call.started_at.label("started_at_col"),
                Call.ended_at.label("ended_at_col"),
                Call.duration_seconds.label("duration_col"),
                Agent.name.label("agent_name_col"),
            )
        )

    def _row_to_response(self, row, summary_only: bool = False) -> Dict[str, Any]:
        metric, call_id, agent_id, started_at, ended_at, duration_seconds, agent_name = row
        return self.call_metrics_response(
            metric=metric,
            call_id=call_id,
            agent_id=agent_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            agent_name=agent_name,
            summary_only=summary_only,
        )

    def list_metrics(
        self,
        page_no: int = 1,
        page_size: int = 10,
        start_date_time: Optional[str] = None,
        end_date_time: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        base_query = self._base_query()

        if start_date_time is not None:
            base_query = base_query.filter(Call.started_at >= start_date_time)
        if end_date_time is not None:
            base_query = base_query.filter(Call.started_at <= end_date_time)

        if filters:
            for f in filters:
                base_query = self._apply_filter(base_query, f)

        total = base_query.count()

        sort_col = self._COLUMN_MAP.get(sort_by) if sort_by else None
        if sort_col is None:
            sort_col = Call.started_at
        order_fn = asc if sort_order == "asc" else desc
        base_query = base_query.order_by(order_fn(sort_col))

        offset = (page_no - 1) * page_size
        results = base_query.offset(offset).limit(page_size).all()

        return {
            "data": [self._row_to_response(row, summary_only=True) for row in results],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def _apply_filter(self, query, f: Dict[str, Any]):
        field = f.get("field")
        operator = f.get("operator")
        value = f.get("value")
        col = self._COLUMN_MAP.get(field)
        if col is None:
            return query
        if operator == "equal_to":
            return query.filter(col == value)
        if operator == "greater_than":
            return query.filter(col > value)
        if operator == "less_than":
            return query.filter(col < value)
        if operator == "between" and isinstance(value, list) and len(value) == 2:
            return query.filter(col.between(value[0], value[1]))
        if operator == "in" and isinstance(value, list):
            return query.filter(col.in_(value))
        if operator == "contains":
            return query.filter(col.ilike(f"%{value}%"))
        return query

    def get_by_call_id(self, call_id: str) -> Optional[Dict[str, Any]]:
        row = self._base_query().filter(CallMetrics.call_id == call_id).first()
        if not row:
            return None
        return self._row_to_response(row)

    # ------------------------------------------------------------------
    # Formatter
    # ------------------------------------------------------------------

    def call_metrics_response(
        self,
        metric: CallMetrics,
        call_id=None,
        agent_id=None,
        started_at=None,
        ended_at=None,
        duration_seconds: Optional[int] = None,
        agent_name: Optional[str] = None,
        summary_only: bool = False,
    ) -> Dict[str, Any]:
        """Format a CallMetrics row for the API.

        ``summary_only=True`` returns identifiers + derived scalars only
        (used by ``list_metrics`` to keep the page payload small). The full
        per-sample arrays are still loaded from the DB to compute the
        scalars, but they are dropped from the response body.

        ``summary_only=False`` (default) returns the full payload including
        the six metric arrays — used by ``get_by_call_id`` so the modal
        can render the full breakdown when a row is clicked.
        """
        arrays = {field: (getattr(metric, field) or []) for field in _METRIC_FIELDS}

        response: Dict[str, Any] = {
            "id": str(metric.id),
            "call_id": str(call_id or metric.call_id),
            "agent_id": str(agent_id) if agent_id is not None else None,
            "agent_name": agent_name,
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
            "duration_seconds": duration_seconds,

            "avg_ttfb_ms": _avg(s.get("value") for s in arrays["ttfb"]),
            "p99_ttfb_ms": _percentile((s.get("value") for s in arrays["ttfb"]), 0.99),
            "avg_latency_s": _avg(s.get("latency") for s in arrays["user_bot_latency"]),
            "p99_latency_s": _percentile(
                (s.get("latency") for s in arrays["user_bot_latency"]), 0.99
            ),
            "total_tokens": _sum(s.get("total_tokens") for s in arrays["llm_usage"]),
            "total_tts_chars": _sum(s.get("characters") for s in arrays["tts_usage"]),
            "total_stt_audio_ms": _sum(s.get("audio_ms") for s in arrays["stt_usage"]),
            "turn_count": len(arrays["turns"]),
        }

        if not summary_only:
            for field, value in arrays.items():
                response[field] = value

        return response


def _avg(values) -> Optional[float]:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 3)


def _sum(values) -> int:
    return sum(v for v in values if isinstance(v, (int, float)))


def _percentile(values, q: float) -> Optional[float]:
    # Linear interpolation between adjacent ranks — same convention as numpy's
    # default. With small N (typical for a single call) p99 collapses to max,
    # which is the right behavior: the worst observed sample is the worst
    # 1%-ile estimate we can give.
    nums = sorted(v for v in values if isinstance(v, (int, float)))
    if not nums:
        return None
    if len(nums) == 1:
        return round(nums[0], 3)
    rank = q * (len(nums) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(nums) - 1)
    frac = rank - lo
    return round(nums[lo] + (nums[hi] - nums[lo]) * frac, 3)
