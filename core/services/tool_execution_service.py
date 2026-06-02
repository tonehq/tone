"""Persist tool / MCP-tool invocations to the ``tool_executions`` table.

Tool handlers (custom, built-in, document, MCP) collect their invocations into
an in-memory ``tool_call_entries`` list during a call. At call completion,
``CallLogService.complete_call`` hands that list here to be written as one row
per invocation — making each call queryable for debugging.
"""

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from core.models.tool_execution import ToolExecution
from core.services.base import BaseService

# Tool args/outputs can be huge; cap what we store per field so a single big
# payload can't bloat the table.
_VALUE_LIMIT = 8000


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable, size-capped version of ``value``.

    JSONB can store strings/numbers/lists/dicts directly. Anything that isn't
    natively serializable falls back to ``str()``. Oversized strings are
    truncated with a marker so we never persist multi-MB blobs.
    """
    if value is None:
        return None
    try:
        # Round-trip through json to guarantee it's storable, coercing exotic
        # types (datetimes, MCP result objects, etc.) via default=str.
        safe = json.loads(json.dumps(value, default=str))
    except Exception:
        safe = str(value)

    if isinstance(safe, str) and len(safe) > _VALUE_LIMIT:
        return f"{safe[:_VALUE_LIMIT]}… [truncated {len(safe) - _VALUE_LIMIT} chars]"
    return safe


# Keys mapped to dedicated columns; everything else lands in meta_data.
_MAPPED_KEYS = {
    "tool", "tool_type", "server", "arguments", "result", "output",
    "status", "error", "status_code", "duration_ms", "turn", "timestamp",
}


class ToolExecutionService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    def record_executions(self, call_id, agent_id, entries: List[dict]) -> int:
        """Insert one ToolExecution row per entry. Returns the count written.

        Never raises on a bad individual entry — it logs and skips, so a single
        malformed entry can't lose the rest (and the caller wraps this in its
        own try/except so call completion is never blocked)."""
        if not entries:
            return 0

        rows = []
        for entry in entries:
            try:
                rows.append(self._row_from_entry(call_id, agent_id, entry))
            except Exception as e:
                logger.error("Skipping malformed tool_call entry {}: {}", entry, e)

        if not rows:
            return 0

        self.db.add_all(rows)
        self.db.commit()
        return len(rows)

    def _row_from_entry(self, call_id, agent_id, entry: dict) -> ToolExecution:
        result = entry.get("result")
        if result is None:
            result = entry.get("output")
        error = entry.get("error")

        # Status: prefer an explicit field, else infer from error/result shape.
        status = entry.get("status")
        if not status:
            if error:
                status = "error"
            elif isinstance(result, str) and result.strip().lower().startswith("error"):
                status = "error"
            else:
                status = "success"

        started_at = None
        ts = entry.get("timestamp")
        if ts is not None:
            try:
                started_at = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except (ValueError, OSError, TypeError):
                started_at = None

        meta = {k: v for k, v in entry.items() if k not in _MAPPED_KEYS}

        return ToolExecution(
            organization_id=self.org_id,
            call_id=call_id,
            agent_id=agent_id,
            tool_name=entry.get("tool") or "unknown",
            tool_type=entry.get("tool_type"),
            mcp_server_name=entry.get("server"),
            arguments=_json_safe(entry.get("arguments")),
            result=_json_safe(result),
            status=status,
            error_message=str(error) if error is not None else None,
            status_code=entry.get("status_code"),
            duration_ms=entry.get("duration_ms"),
            turn_number=entry.get("turn"),
            started_at=started_at,
            meta_data=_json_safe(meta) if meta else None,
        )
