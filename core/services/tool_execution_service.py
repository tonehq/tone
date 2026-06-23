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

from core.models.mcp_server import McpServer
from core.models.tool import Tool
from core.models.tool_execution import ToolExecution
from core.services.base import BaseService

# Status / type values that are valid filter inputs from the API. Anything
# outside these lists is treated as "no filter" so the endpoint can't be used
# to probe arbitrary column values.
_VALID_STATUSES = {"success", "error"}
_VALID_TOOL_TYPES = {"custom", "send_sms", "google_calendar", "read_document", "mcp", "built_in"}

# Hard cap on rows returned by ``list_for_call`` — a sane call rarely has >50
# invocations, so 500 leaves plenty of headroom while protecting the response
# (and the FE table) from a runaway agent that loops on a failing tool.
_LIST_HARD_LIMIT = 500

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
    "tool_id", "mcp_server_id",
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

    def list_for_call(
        self,
        call_id,
        status: Optional[str] = None,
        tool_type: Optional[str] = None,
    ) -> List[dict]:
        """Return all tool executions for a call as dicts, newest invocation last.

        Ordered by ``started_at`` then by row ``id`` so the UI shows them in the
        same sequence the agent actually invoked them. Org scoping comes from
        ``BaseService.query`` — no need to filter on ``organization_id`` here.
        Unknown ``status`` / ``tool_type`` values are silently ignored.
        """
        # LEFT JOIN tools / mcp_servers on the stable FKs (NOT on name).
        # NULL joined columns are returned as-is — happens for code-defined
        # built-ins (no `tools` row), pre-migration rows, and tools/servers
        # the user has since deleted (FK was SET NULL).
        q = (
            self.query(ToolExecution)
            .outerjoin(Tool, Tool.id == ToolExecution.tool_id)
            .outerjoin(McpServer, McpServer.id == ToolExecution.mcp_server_id)
            .add_columns(
                Tool.description.label("tool_description"),
                Tool.url.label("tool_url"),
                Tool.method.label("tool_method"),
                Tool.auth_type.label("tool_auth_type"),
                Tool.is_active.label("tool_is_active"),
                McpServer.description.label("mcp_server_description"),
                McpServer.server_url.label("mcp_server_url"),
                McpServer.transport_type.label("mcp_server_transport"),
                McpServer.is_active.label("mcp_server_is_active"),
            )
            .filter(ToolExecution.call_id == call_id)
        )

        if status in _VALID_STATUSES:
            q = q.filter(ToolExecution.status == status)
        if tool_type in _VALID_TOOL_TYPES:
            q = q.filter(ToolExecution.tool_type == tool_type)

        rows = (
            q.order_by(ToolExecution.started_at.asc().nulls_last(), ToolExecution.id.asc())
            .limit(_LIST_HARD_LIMIT)
            .all()
        )

        out: List[dict] = []
        for row in rows:
            execution = row[0]
            payload = execution.to_dict()
            payload.update({
                "tool_description": row.tool_description,
                "tool_url": row.tool_url,
                "tool_method": row.tool_method,
                "tool_auth_type": row.tool_auth_type,
                "tool_is_active": row.tool_is_active,
                "mcp_server_description": row.mcp_server_description,
                "mcp_server_url": row.mcp_server_url,
                "mcp_server_transport": row.mcp_server_transport,
                "mcp_server_is_active": row.mcp_server_is_active,
            })
            out.append(payload)
        return out

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
            tool_id=entry.get("tool_id"),
            mcp_server_id=entry.get("mcp_server_id"),
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
