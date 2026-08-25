"""Shared helpers that map workflow graph node ids to human-readable names.

The playbook serializer (`serialize_graph_for_llm`) needs two lookups so the
markdown it emits names tools by their agent-visible name, not opaque UUIDs:

- ``workflow_tool_names``   — `{toolId | mcpServerId → display name}`
- ``workflow_api_fn_names`` — `{apiRequest node_id → sanitized fn name}`

Both the runtime pipeline (``core/services/pipeline/service_resolver.py``) and
the LLM-eval loader (``core/services/evals/agent_llm/agent_config_loader.py``)
call these so the playbook the judge grades against is byte-identical to the
playbook the bot actually runs.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session


def workflow_tool_names(db: Session, graph: dict, org_id=None) -> dict:
    """Map each tool node's ``toolId`` / ``mcpServerId`` → display name so the
    serialized steps can name the exact (agent-attached) tool or MCP server to
    use. Org-scoped; returns ``{}`` when there are no tool/MCP ids."""
    nodes = graph.get("nodes") or []
    tool_ids, mcp_ids = [], []
    for n in nodes:
        data = (n or {}).get("data") or {}
        if data.get("toolId"):
            tool_ids.append(data["toolId"])
        if data.get("mcpServerId"):
            mcp_ids.append(data["mcpServerId"])
    names: dict = {}
    if tool_ids:
        from core.models.tool import Tool

        q = db.query(Tool).filter(Tool.id.in_(tool_ids))
        if org_id:
            q = q.filter(Tool.organization_id == org_id)
        names.update({str(t.id): t.name for t in q.all()})
    if mcp_ids:
        from core.models.mcp_server import McpServer

        q = db.query(McpServer).filter(McpServer.id.in_(mcp_ids))
        if org_id:
            q = q.filter(McpServer.organization_id == org_id)
        names.update({str(m.id): m.name for m in q.all()})
    return names


def workflow_api_fn_names(graph: dict, taken: Optional[set] = None) -> dict:
    """Map each apiRequest node id → the unique sanitized function name it is
    registered under, deduped among themselves AND against ``taken`` (the
    agent's real tool names). The playbook serializer and the synthesized
    tools share this map so the function names the model is told to call
    match the names actually registered."""
    from core.services.custom_tool_service import sanitize_tool_name

    claimed = set(taken or ())
    names: dict = {}
    for n in (graph.get("nodes") or []):
        if not isinstance(n, dict) or n.get("type") != "apiRequest":
            continue
        nid = n.get("id")
        d = n.get("data") or {}
        raw = (d.get("name") or nid or "api_request").strip()
        fn = sanitize_tool_name(raw)
        if fn in claimed:
            i = 2
            while f"{fn}_{i}" in claimed:
                i += 1
            fn = f"{fn}_{i}"
        claimed.add(fn)
        names[str(nid)] = fn
    return names


__all__ = ["workflow_tool_names", "workflow_api_fn_names"]
