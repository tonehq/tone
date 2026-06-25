from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import Float, and_, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Query, Session, aliased

from core.models.agent import Agent
from core.models.call import Call
from core.models.call_metrics import CallMetrics
from core.models.channel import Channel
from core.models.phone_number import PhoneNumber
from core.models.upload import Upload
from core.services.base import BaseService
from core.services.r2_storage_service import R2StorageService


class CallService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_filter_values(self, column_name: str) -> Dict[str, Any]:
        # JSONB path expressions for pipeline_config — distinct values come from
        # the snapshot written at call start (see CallLogService.create_call_log).
        pipeline_paths = {
            "llm_provider": Call.pipeline_config["llm"]["provider_name"].astext,
            "llm_model": Call.pipeline_config["llm"]["model_name"].astext,
            "stt_provider": Call.pipeline_config["stt"]["provider_name"].astext,
            "stt_model": Call.pipeline_config["stt"]["model_name"].astext,
            "tts_provider": Call.pipeline_config["tts"]["provider_name"].astext,
            "tts_model": Call.pipeline_config["tts"]["model_name"].astext,
        }
        allowed = {
            "status": None,
            "direction": Call.direction,
            "agent_name": None,
            "agent_type": None,
            "channel_type": None,
            **pipeline_paths,
        }

        if column_name not in allowed:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column: {column_name}. Allowed: {', '.join(sorted(allowed.keys()))}",
            )

        base = self.query(Call).join(Agent, Call.agent_id == Agent.id)

        # Drop NULL and empty-string distinct values so legacy rows with
        # partial JSONB (e.g. {"llm": {"provider_name": ""}}) don't surface a
        # blank dropdown option.
        def _clean(rs):
            return sorted([r[0] for r in rs if r[0] is not None and r[0] != ""])

        if column_name == "agent_name":
            rows = base.with_entities(Agent.name).distinct().all()
            values = _clean(rows)
        elif column_name == "agent_type":
            rows = base.with_entities(Agent.agent_type).distinct().all()
            values = _clean(rows)
        elif column_name == "channel_type":
            rows = (
                base.join(Channel, Call.channel_id == Channel.id)
                .with_entities(Channel.channel_type)
                .distinct()
                .all()
            )
            values = _clean(rows)
        elif column_name == "status":
            # Status is derived: ended_at IS NOT NULL → completed, else in_progress
            values = ["completed", "in_progress"]
        else:
            col = allowed[column_name]
            rows = base.with_entities(col).distinct().all()
            values = _clean(rows)

        return {"column": column_name, "values": values}

    # ------------------------------------------------------------------
    # Filtering helpers (shared by get_calls and get_facets)
    # ------------------------------------------------------------------

    def _filter_column_map(self) -> Dict[str, Any]:
        """Map filter/sort field names to their SQLAlchemy column expressions.

        ``status`` is None because it is derived from (ended_at, metadata) and
        handled specially in :meth:`_apply_filters`.
        """
        return {
            "status": None,  # derived, handled specially
            "direction": Call.direction,
            "duration_seconds": Call.duration_seconds,
            "started_at": Call.started_at,
            "ended_at": Call.ended_at,
            "agent_id": Agent.id,
            "agent_name": Agent.name,
            "agent_type": Agent.agent_type,
            "channel_type": Channel.channel_type,
            # JSONB snapshot of LLM/STT/TTS used to serve the call.
            "llm_provider": Call.pipeline_config["llm"]["provider_name"].astext,
            "llm_model": Call.pipeline_config["llm"]["model_name"].astext,
            "stt_provider": Call.pipeline_config["stt"]["provider_name"].astext,
            "stt_model": Call.pipeline_config["stt"]["model_name"].astext,
            "tts_provider": Call.pipeline_config["tts"]["provider_name"].astext,
            "tts_model": Call.pipeline_config["tts"]["model_name"].astext,
            # Computed: length of CallMetrics.turns JSONB array. NULL (calls
            # without metrics or with non-array turns) is excluded by BETWEEN.
            "turn_count": func.jsonb_array_length(CallMetrics.turns),
            # Computed: AVG(latency) over CallMetrics.user_bot_latency JSONB
            # array elements ({"latency": float}). NULL (no metrics / empty
            # array) is excluded by BETWEEN, matching turn_count semantics.
            "avg_latency_seconds": (
                select(
                    func.avg(
                        cast(
                            func.jsonb_array_elements(CallMetrics.user_bot_latency)
                            .column_valued('e')
                            .op('->>')('latency'),
                            Float,
                        )
                    )
                ).scalar_subquery()
            ),
        }

    def _status_predicates(self) -> Dict[str, Any]:
        """Map each derived call status to its SQL predicate.

        Status is derived from (Call.ended_at, Call.metadata_['status']):
          failed       → metadata.status == 'failed'
          completed    → ended_at IS NOT NULL AND not failed
          in_progress  → ended_at IS NULL

        NOTE: coalesce(NULL, "") is required because most rows have
        metadata_ = NULL (only fail_call writes it). Without coalesce,
        `metadata_['status'].astext` returns SQL NULL, ~NULL is NULL, and the
        WHERE clause drops every row. Shared by :meth:`_apply_filters` (status
        filter) and :meth:`get_facets` (per-status counts) so the taxonomy lives
        in one place.
        """
        status_text = func.coalesce(Call.metadata_["status"].astext, "")
        is_failed = status_text == "failed"
        return {
            "completed": and_(Call.ended_at.isnot(None), ~is_failed),
            "in_progress": Call.ended_at.is_(None),
            "failed": is_failed,
        }

    def _apply_filters(
        self,
        query: Query,
        filters: Optional[List[Dict[str, Any]]],
        column_map: Optional[Dict[str, Any]] = None,
        exclude_field: Optional[str] = None,
    ) -> Query:
        """Apply a list of {field, operator, value} filters to ``query``.

        Returns a new ``Query`` (filters are applied immutably, never in place).
        ``exclude_field`` skips one field — used by faceting so a facet's own
        selection doesn't constrain its own counts (Vercel semantics).
        """
        if not filters:
            return query
        if column_map is None:
            column_map = self._filter_column_map()

        for f in filters:
            field = f.get("field")
            operator = f.get("operator")
            value = f.get("value")

            if exclude_field is not None and field == exclude_field:
                continue

            if field == "status":
                # Selecting multiple statuses ORs the predicates together; see
                # _status_predicates for how each state is derived.
                if operator == "in" and isinstance(value, list):
                    predicates = self._status_predicates()
                    preds = [predicates[v] for v in value if v in predicates]
                    if preds:
                        query = query.filter(or_(*preds))
                continue

            col = column_map.get(field)
            if col is None:
                continue

            if operator == "equal_to":
                query = query.filter(col == value)
            elif operator == "greater_than":
                query = query.filter(col > value)
            elif operator == "less_than":
                query = query.filter(col < value)
            elif operator == "between":
                if isinstance(value, list) and len(value) == 2:
                    query = query.filter(col.between(value[0], value[1]))
            elif operator == "in":
                if isinstance(value, list):
                    query = query.filter(col.in_(value))
            elif operator == "contains":
                query = query.filter(col.ilike(f"%{value}%"))

        return query

    def get_facets(
        self,
        start_date_time: Optional[str] = None,
        end_date_time: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Per-value counts for each facet field, for the filter drawer.

        Each facet reflects the active date range and every *other* active
        filter, but NOT its own selection — so toggling a value within a facet
        doesn't zero out its siblings (Vercel-style faceting).
        """
        column_map = self._filter_column_map()
        # Faceted (non-numeric, checkbox) fields and their column expressions.
        facet_fields = [
            "status",
            "agent_name",
            "direction",
            "channel_type",
            "llm_model",
            "stt_model",
            "tts_model",
        ]
        FACET_LIMIT = 50

        def _base():
            q = (
                self.query(Call)
                .join(Agent, Call.agent_id == Agent.id)
                .join(Channel, Call.channel_id == Channel.id)
                # 1:1 outerjoin keeps row count == call count so COUNT(*) is the
                # number of calls; also lets turn_count/avg_latency filters apply.
                .outerjoin(CallMetrics, CallMetrics.call_id == Call.id)
            )
            if start_date_time is not None:
                q = q.filter(Call.started_at >= start_date_time)
            if end_date_time is not None:
                q = q.filter(Call.started_at <= end_date_time)
            return q

        result: Dict[str, List[Dict[str, Any]]] = {}

        for field in facet_fields:
            scoped = self._apply_filters(
                _base(), filters, column_map=column_map, exclude_field=field
            )

            if field == "status":
                predicates = self._status_predicates()
                # One query, one filtered COUNT per state (Postgres FILTER
                # clause), instead of a round-trip per status.
                row = scoped.with_entities(
                    *[func.count().filter(pred).label(name) for name, pred in predicates.items()]
                ).one()
                # Fixed enum set — emit all three even when zero (Vercel shows
                # zero-count rows for known levels).
                result[field] = [
                    {"value": name, "count": getattr(row, name)} for name in predicates
                ]
                continue

            col = column_map.get(field)
            rows = (
                scoped.with_entities(col, func.count())
                .group_by(col)
                .order_by(func.count().desc())
                .limit(FACET_LIMIT)
                .all()
            )
            result[field] = [
                {"value": value, "count": count}
                for value, count in rows
                if value is not None and value != ""
            ]

        return result

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
            # 1:1 on call_id (unique) — keeps row count equal to call count
            # so pagination math is unaffected.
            .outerjoin(CallMetrics, CallMetrics.call_id == Call.id)
        )

        if start_date_time is not None:
            base_query = base_query.filter(Call.started_at >= start_date_time)
        if end_date_time is not None:
            base_query = base_query.filter(Call.started_at <= end_date_time)

        # Column mapping for filters and sorting (shared with get_facets).
        column_map = self._filter_column_map()
        base_query = self._apply_filters(base_query, filters, column_map=column_map)

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
                CallMetrics.id.label("metrics_id"),
                CallMetrics.ttfb.label("metrics_ttfb"),
                CallMetrics.processing.label("metrics_processing"),
                CallMetrics.llm_usage.label("metrics_llm_usage"),
                CallMetrics.tts_usage.label("metrics_tts_usage"),
                CallMetrics.stt_usage.label("metrics_stt_usage"),
                CallMetrics.user_bot_latency.label("metrics_user_bot_latency"),
                CallMetrics.turns.label("metrics_turns"),
                CallMetrics.turn_metrics.label("metrics_turn_metrics"),
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
                metrics=self._metrics_payload(
                    metrics_id=row[6],
                    ttfb=row[7],
                    processing=row[8],
                    llm_usage=row[9],
                    tts_usage=row[10],
                    stt_usage=row[11],
                    user_bot_latency=row[12],
                    turns=row[13],
                    turn_metrics=row[14],
                ),
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
            # Mirror /list so the single-call response carries the joined
            # CallMetrics record under the `metrics` key.
            .outerjoin(CallMetrics, CallMetrics.call_id == Call.id)
            .add_columns(
                Agent.name.label("agent_name"),
                Agent.agent_type.label("agent_type"),
                Channel.channel_type.label("channel_type"),
                from_pn.number.label("from_number"),
                to_pn.number.label("to_number"),
                CallMetrics.id.label("metrics_id"),
                CallMetrics.ttfb.label("metrics_ttfb"),
                CallMetrics.processing.label("metrics_processing"),
                CallMetrics.llm_usage.label("metrics_llm_usage"),
                CallMetrics.tts_usage.label("metrics_tts_usage"),
                CallMetrics.stt_usage.label("metrics_stt_usage"),
                CallMetrics.user_bot_latency.label("metrics_user_bot_latency"),
                CallMetrics.turns.label("metrics_turns"),
                CallMetrics.turn_metrics.label("metrics_turn_metrics"),
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
            metrics=self._metrics_payload(
                metrics_id=result[6],
                ttfb=result[7],
                processing=result[8],
                llm_usage=result[9],
                tts_usage=result[10],
                stt_usage=result[11],
                user_bot_latency=result[12],
                turns=result[13],
                turn_metrics=result[14],
            ),
        )

    def get_audio_url(self, call_id: str) -> Dict[str, Any]:
        call = self.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        if not call.recording_upload_id:
            raise HTTPException(status_code=404, detail="No recording available for this call")

        upload = self.db.query(Upload).filter(Upload.id == call.recording_upload_id).first()
        if not upload or not upload.file_path:
            raise HTTPException(status_code=404, detail="Recording file not found")

        url = R2StorageService().generate_presigned_url(upload.file_path)
        return {"url": url}

    def _metrics_payload(
        self,
        metrics_id,
        ttfb,
        processing,
        llm_usage,
        tts_usage,
        stt_usage,
        user_bot_latency,
        turns,
        turn_metrics=None,
    ) -> Optional[Dict[str, Any]]:
        # Outer join returns all-NULL columns when no metrics row exists; surface
        # that as `None` so the FE can branch on row.metrics == null.
        if metrics_id is None:
            return None
        return {
            "id": str(metrics_id),
            "ttfb": ttfb or [],
            "processing": processing or [],
            "llm_usage": llm_usage or [],
            "tts_usage": tts_usage or [],
            "stt_usage": stt_usage or [],
            "user_bot_latency": user_bot_latency or [],
            "turns": turns or [],
            "turn_metrics": turn_metrics or [],
        }

    def call_response(
        self,
        call: Call,
        agent_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        channel_type: Optional[str] = None,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = call.metadata_ or {}
        # Failure is stored on metadata.status by CallLogService.fail_call,
        # which also sets ended_at. Check failure first so failed calls are not
        # mis-reported as "completed".
        if metadata.get("status") == "failed":
            status = "failed"
        elif call.ended_at:
            status = "completed"
        else:
            status = "in_progress"

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
            "recording_duration_seconds": call.recording_duration_seconds,
            "from_number": from_number or call.from_number_raw_by_provider,
            "to_number": to_number,
            "provider_call_id": call.provider_call_id,
            "trace_id": call.trace_id,
            "recording_upload_id": str(call.recording_upload_id) if call.recording_upload_id else None,
            "transcript": metadata.get("transcript"),
            "tool_calls": metadata.get("tool_calls"),
            "pipeline_config": call.pipeline_config,
            "metrics": metrics,
        }
