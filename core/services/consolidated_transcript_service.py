"""Consolidated per-turn view of a completed call.

Merges the three raw sources we already persist — transcript entries (in
``call.metadata_["transcript"]``), ``tool_executions`` rows, and
``call_metrics.turn_metrics`` — into a single per-turn dict shape that
downstream UIs (call detail page, analytics) can render without cross-joining
JSONB and a normalized table on every request.

Read-only over the raw sources: the transcript / tool_executions /
turn_metrics tables are the source of truth. This is a derived view written
to the dedicated ``calls.consolidated_transcript`` JSONB column at post-call
time (see the ``a9c1e5b3d7f2_add_consolidated_transcript_to_calls`` migration).

Per-turn output shape::

    {
        "turn_number": int,
        "user_speech": str | None,          # concatenated user transcript text for the turn
        "bot_speech": str | None,           # concatenated assistant transcript text for the turn
        "tool_calls": [dict, ...],          # ToolExecution.to_dict() payloads, ordered
        "user_bot_latency_ms": int | None,  # end_to_end from turn_metrics, converted to ms
    }
"""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from loguru import logger

from core.models.call import Call
from core.models.call_metrics import CallMetrics
from core.models.tool_execution import ToolExecution
from core.services.base import BaseService


class ConsolidatedTranscriptService(BaseService):
    """Build and persist the ``calls.consolidated_transcript`` JSONB column."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_and_store(self, call_id: UUID) -> Optional[List[dict]]:
        """End-to-end: load the sources, consolidate, write to the column.

        Returns the consolidated list (also written to the call row), or
        ``None`` if the call doesn't exist. Idempotent — re-running for the
        same call recomputes and overwrites the column.
        """
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            logger.warning("[consolidated_transcript] call {} not found; skipping", call_id)
            return None

        transcript = self._extract_transcript(call)
        tool_executions = self._load_tool_executions(call_id)
        turn_metrics = self._load_turn_metrics(call_id)

        consolidated = self.consolidate(
            transcript=transcript,
            tool_executions=tool_executions,
            turn_metrics=turn_metrics,
        )

        self._persist(call, consolidated)
        self.db.commit()
        logger.info(
            "[consolidated_transcript] call={} turns={}", call_id, len(consolidated),
        )
        return consolidated

    # ------------------------------------------------------------------
    # Pure consolidation (no DB) — kept public so it can be unit tested
    # ------------------------------------------------------------------

    def consolidate(
        self,
        transcript: List[dict],
        tool_executions: List[ToolExecution],
        turn_metrics: List[dict],
    ) -> List[dict]:
        """Group three raw streams by ``turn_number`` and emit one dict per turn.

        Turns with no data on any axis (i.e. never referenced) are omitted.
        Entries lacking a turn number are dropped — they can't be joined.
        """
        transcript_by_turn = self._group_transcript(transcript)
        tools_by_turn = self._group_tool_executions(tool_executions)
        latency_by_turn = self._group_turn_latency(turn_metrics)

        turn_numbers = sorted(
            set(transcript_by_turn) | set(tools_by_turn) | set(latency_by_turn)
        )

        return [
            {
                "turn_number": turn_number,
                "user_speech": self._join_role(
                    transcript_by_turn.get(turn_number, []), role="user"
                ),
                "bot_speech": self._join_role(
                    transcript_by_turn.get(turn_number, []), role="assistant"
                ),
                "tool_calls": [
                    exec_.to_dict() for exec_ in tools_by_turn.get(turn_number, [])
                ],
                "user_bot_latency_ms": latency_by_turn.get(turn_number),
            }
            for turn_number in turn_numbers
        ]

    # ------------------------------------------------------------------
    # Source loaders
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_transcript(call: Call) -> List[dict]:
        metadata = call.metadata_ or {}
        transcript = metadata.get("transcript") or []
        return transcript if isinstance(transcript, list) else []

    def _load_tool_executions(self, call_id: UUID) -> List[ToolExecution]:
        """All tool_executions for the call, ordered by invocation time.

        Ordering matches ``ToolExecutionService.list_for_call`` so a UI that
        renders tool_calls[] gets them in the same sequence the agent invoked
        them. Org scoping comes from ``BaseService.query``.
        """
        return (
            self.query(ToolExecution)
            .filter(ToolExecution.call_id == call_id)
            .order_by(
                ToolExecution.started_at.asc().nulls_last(),
                ToolExecution.id.asc(),
            )
            .all()
        )

    def _load_turn_metrics(self, call_id: UUID) -> List[dict]:
        row = (
            self.db.query(CallMetrics.turn_metrics)
            .filter(CallMetrics.call_id == call_id)
            .first()
        )
        if not row or not row[0]:
            return []
        return row[0] if isinstance(row[0], list) else []

    # ------------------------------------------------------------------
    # Grouping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_transcript(transcript: List[dict]) -> Dict[int, List[dict]]:
        buckets: Dict[int, List[dict]] = {}
        for entry in transcript:
            turn = entry.get("turn_number")
            if turn is None:
                continue
            buckets.setdefault(int(turn), []).append(entry)
        return buckets

    @staticmethod
    def _group_tool_executions(
        executions: List[ToolExecution],
    ) -> Dict[int, List[ToolExecution]]:
        buckets: Dict[int, List[ToolExecution]] = {}
        for execution in executions:
            turn = execution.turn_number
            if turn is None:
                continue
            buckets.setdefault(int(turn), []).append(execution)
        return buckets

    @staticmethod
    def _group_turn_latency(turn_metrics: List[dict]) -> Dict[int, Optional[int]]:
        """Map turn_number → user-perceived latency in ms.

        ``turn_metrics[i]["end_to_end"]`` is the wall-clock seconds from
        user-stopped to bot-started (see ``_finalize_buffer`` in
        ``metrics_collector.py``). Converted to ms and rounded so the JSONB
        value is a plain int the UI can render directly.
        """
        latencies: Dict[int, Optional[int]] = {}
        for row in turn_metrics:
            turn = row.get("turn")
            if turn is None:
                continue
            end_to_end = row.get("end_to_end")
            latencies[int(turn)] = (
                int(round(end_to_end * 1000)) if end_to_end is not None else None
            )
        return latencies

    @staticmethod
    def _join_role(entries: List[dict], role: str) -> Optional[str]:
        """Concatenate transcript text for a single role within one turn.

        A turn can contain multiple utterances of the same role (e.g. user
        hesitates then continues). Joining with a space matches how the
        legacy transcript view already renders the same content.
        """
        parts = [
            (entry.get("text") or "").strip()
            for entry in entries
            if entry.get("role") == role and (entry.get("text") or "").strip()
        ]
        if not parts:
            return None
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _persist(call: Call, consolidated: List[dict]) -> None:
        # Assign to the dedicated JSONB column. Reassigning (rather than
        # mutating an existing value) is how SQLAlchemy tracks JSONB changes.
        call.consolidated_transcript = consolidated
