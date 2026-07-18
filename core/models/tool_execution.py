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

    ``status`` captures the full LLM lifecycle for the call, not just the
    handler outcome:

    * ``proposed``  — LLM emitted a tool call but the handler never ran
                      (e.g. tool name is unregistered).
    * ``cancelled`` — proposed then killed before completing (e.g. user
                      interrupted the call mid-invocation).
    * ``success``   — handler ran to completion without error.
    * ``error``     — handler ran but returned / raised an error.
    """

    __tablename__ = "tool_executions"

    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)

    tool_name = Column(String(255), nullable=False)
    tool_type = Column(String(50), nullable=True)  # custom | send_sms | google_calendar | read_document | mcp | built_in
    mcp_server_name = Column(String(255), nullable=True)  # set only for MCP tools

    # Stable FKs back to the source records — set at write time when the
    # tool / MCP server is a row in the DB. Both nullable: code-defined
    # built-ins like `end_call` and `read_document` have no `tools` row, and
    # pre-migration rows have NULL here. ON DELETE SET NULL so a renamed or
    # deleted tool only nulls the join, never deletes the execution row.
    tool_id = Column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    mcp_server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    # Pipecat's per-call correlation id for the FunctionCallFromLLM. Threaded
    # through the proposal → in-progress → result frames so a proposed row
    # (never executed) and an executed row for the same LLM decision share
    # the same key. Nullable because pre-migration rows lack it.
    tool_call_id = Column(String(128), nullable=True, index=True)

    arguments = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)

    status = Column(String(20), nullable=True)  # proposed | success | error | cancelled
    error_message = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)  # HTTP status (webhook/built-in tools)

    duration_ms = Column(Integer, nullable=True)
    turn_number = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)

    # Lifecycle timestamps (all UTC). ``started_at`` above is kept for backward
    # compatibility with older readers and is dual-written alongside ``invoked_at``.
    # ``proposed_at`` is set the moment pipecat pushes ``FunctionCallsStartedFrame``
    # for this tool_call_id — captured even when the tool never executes (LLM
    # hallucinated a tool name, user interrupted before dispatch, etc.).
    proposed_at = Column(DateTime(timezone=True), nullable=True)
    llm_requested_at = Column(DateTime(timezone=True), nullable=True)
    invoked_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    meta_data = Column(JSONB, nullable=True, default=dict)  # catch-all for extra fields

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "call_id": str(self.call_id) if self.call_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "mcp_server_name": self.mcp_server_name,
            "tool_id": str(self.tool_id) if self.tool_id else None,
            "mcp_server_id": str(self.mcp_server_id) if self.mcp_server_id else None,
            "tool_call_id": self.tool_call_id,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status,
            "error_message": self.error_message,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "turn_number": self.turn_number,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "proposed_at": self.proposed_at.isoformat() if self.proposed_at else None,
            "llm_requested_at": self.llm_requested_at.isoformat() if self.llm_requested_at else None,
            "invoked_at": self.invoked_at.isoformat() if self.invoked_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
