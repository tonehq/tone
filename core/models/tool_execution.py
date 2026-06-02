from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class ToolExecution(OrgScopedModel):
    """One row per tool / MCP-tool invocation during a call.

    Captures everything needed to debug a tool call after the fact: the tool
    name and type, the MCP server it belongs to (for MCP tools), the arguments
    passed in, the result/output, the status, any error, the HTTP status code
    (for webhook/built-in tools), the duration, and the conversation turn.

    Written in batch at call completion (see CallLogService.complete_call). The
    same data also stays in calls.metadata["tool_calls"] (legacy JSONB blob);
    this table makes it queryable per-tool.
    """

    __tablename__ = "tool_executions"

    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)

    tool_name = Column(String(255), nullable=False)
    tool_type = Column(String(50), nullable=True)  # custom | send_sms | google_calendar | read_document | mcp
    mcp_server_name = Column(String(255), nullable=True)  # set only for MCP tools

    arguments = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)

    status = Column(String(20), nullable=True)  # success | error
    error_message = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)  # HTTP status (webhook/built-in tools)

    duration_ms = Column(Integer, nullable=True)
    turn_number = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)

    meta_data = Column(JSONB, nullable=True, default=dict)  # catch-all for extra fields

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "call_id": str(self.call_id) if self.call_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "mcp_server_name": self.mcp_server_name,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status,
            "error_message": self.error_message,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "turn_number": self.turn_number,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
