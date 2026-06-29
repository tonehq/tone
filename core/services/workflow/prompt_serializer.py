"""Render a workflow graph into plain text the LLM can follow.

When an agent runs in ``mode == "workflow"`` (single-prompt pipeline, no turn-by-turn
engine) the assigned workflow's published graph is flattened into a human-readable
"playbook" and appended to the agent's system prompt. The LLM then walks the steps and
branches itself, guided by each node's prompt / first message / extracted variables and
the edge conditions.

The input is the canonical React-Flow-native graph:
    {nodes: [{id, type, position, data:{...}}], edges: [{id, source, target, data:{condition}}],
     globalPrompt, artifactPlan}
"""

from __future__ import annotations

from typing import Any, Dict, List

_TYPE_LABEL = {
    "conversation": "Talk step",
    "decision": "Decision step",
    "tool": "Tool / action step",
    "transferCall": "Transfer step",
    "endCall": "End step",
}


def _s(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def _first_message(data: Dict[str, Any]) -> str:
    plan = data.get("messagePlan")
    if isinstance(plan, dict):
        return _s(plan.get("firstMessage"))
    return ""


def _variables(data: Dict[str, Any]) -> List[str]:
    plan = data.get("variableExtractionPlan")
    out = plan.get("output") if isinstance(plan, dict) else None
    if not isinstance(out, list):
        return []
    names: List[str] = []
    for item in out:
        if isinstance(item, dict):
            title = _s(item.get("title"))
            if title:
                vtype = _s(item.get("type")) or "string"
                names.append(f"{title} ({vtype})")
    return names


def workflow_first_message(graph: Dict[str, Any]) -> str:
    """Return the START node's first message — the opening line the agent speaks on connect.

    Mirrors the entry-point selection in ``serialize_graph_for_llm`` (first ``isStart``
    node). Returns "" when the graph has no start node or it defines no first message.
    """
    if not isinstance(graph, dict):
        return ""
    nodes = graph.get("nodes") or []
    if not isinstance(nodes, list):
        return ""
    start = next(
        (
            n for n in nodes
            if isinstance(n, dict)
            and isinstance(n.get("data"), dict)
            and n["data"].get("isStart")
        ),
        None,
    )
    if start is None:
        return ""
    return _first_message(start.get("data") or {})


def serialize_graph_for_llm(
    graph: Dict[str, Any], tool_names: Dict[str, str] | None = None
) -> str:
    """Flatten a workflow graph into an instruction block for the system prompt.

    ``tool_names`` maps a tool node's ``toolId`` to the tool's display name so the step
    instruction can tell the model exactly which (attached) tool to call. Returns an empty
    string when the graph has no usable nodes.
    """
    tool_names = tool_names or {}
    if not isinstance(graph, dict):
        return ""

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        return ""

    # Outgoing edges grouped by source node id.
    outgoing: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges if isinstance(edges, list) else []:
        if not isinstance(e, dict):
            continue
        src = _s(e.get("source"))
        if src:
            outgoing.setdefault(src, []).append(e)

    # Friendly name per node id (falls back to the id).
    name_by_id: Dict[str, str] = {}
    for n in nodes:
        if isinstance(n, dict):
            nid = _s(n.get("id"))
            data = n.get("data") if isinstance(n.get("data"), dict) else {}
            name_by_id[nid] = _s(data.get("name")) or nid

    lines: List[str] = [
        "# Conversation Workflow",
        "",
        "Follow this step-by-step conversation pathway. Begin at the start step and move "
        "to the next step whose condition matches the caller's response. Speak each step's "
        "message, do what its instructions say, and collect the listed details before moving on.",
    ]

    global_prompt = _s(graph.get("globalPrompt"))
    if global_prompt:
        lines += ["", "## Overall instructions", global_prompt]

    # Order: the (single) start node first, then the rest in their given order. Only the
    # FIRST isStart node is treated as the entry point, matching the runtime engine.
    def _is_start(n: Dict[str, Any]) -> bool:
        data = n.get("data") if isinstance(n.get("data"), dict) else {}
        return bool(data.get("isStart"))

    start_id = next((_s(n.get("id")) for n in nodes if isinstance(n, dict) and _is_start(n)), "")
    start_nodes = [n for n in nodes if isinstance(n, dict) and _s(n.get("id")) == start_id and start_id]
    ordered = start_nodes + [
        n for n in nodes if isinstance(n, dict) and _s(n.get("id")) != start_id
    ]

    lines += ["", "## Steps"]
    for n in ordered:
        nid = _s(n.get("id"))
        ntype = _s(n.get("type")) or "conversation"
        data = n.get("data") if isinstance(n.get("data"), dict) else {}
        label = _TYPE_LABEL.get(ntype, "Step")
        title = name_by_id.get(nid, nid)

        header = f"### {title} — {label}"
        if nid == start_id and start_id:
            header += " [START]"
        if data.get("isGlobal"):
            header += " [GLOBAL — reachable anytime]"
        lines.append("")
        lines.append(header)

        enter_cond = _s(data.get("condition"))
        if data.get("isGlobal") and enter_cond:
            lines.append(f"- Jump here whenever: {enter_cond}")

        fm = _first_message(data)
        if fm:
            # Collapse newlines and escape quotes so the message can't distort the
            # playbook structure injected into the system prompt.
            safe_fm = fm.replace("\n", " ").replace('"', "'")
            lines.append(f'- Say: "{safe_fm}"')

        prompt = _s(data.get("prompt"))
        if prompt:
            lines.append(f"- Do: {prompt}")

        if ntype == "tool":
            tool = data.get("tool") if isinstance(data.get("tool"), dict) else None
            tool_id = _s(data.get("toolId"))
            mcp_id = _s(data.get("mcpServerId"))
            if tool and _s(tool.get("type")):
                lines.append(f"- Run the built-in '{_s(tool.get('type'))}' action.")
            elif tool_id and tool_names.get(tool_id):
                lines.append(
                    f"- Call the `{tool_names[tool_id]}` tool to complete this step. "
                    "Only call it at this step (after the guest has confirmed the details) — "
                    "never earlier in the conversation."
                )
            elif mcp_id and tool_names.get(mcp_id):
                lines.append(
                    f"- Use the `{tool_names[mcp_id]}` MCP server's tools to complete this step. "
                    "Only use them at this step (after the guest has confirmed the details) — "
                    "never earlier in the conversation."
                )
            else:
                lines.append("- Run the configured tool/action for this step.")

        if ntype == "transferCall":
            dest = data.get("destination") if isinstance(data.get("destination"), dict) else {}
            number = _s(dest.get("number"))
            lines.append(f"- Transfer the call{f' to {number}' if number else ''}.")

        if ntype == "endCall":
            lines.append("- End the call after speaking.")

        variables = _variables(data)
        if variables:
            lines.append(f"- Collect: {', '.join(variables)}.")

        branches = outgoing.get(nid, [])
        if branches:
            lines.append("- Next:")
            for e in branches:
                tgt = name_by_id.get(_s(e.get("target")), _s(e.get("target")))
                edata = e.get("data") if isinstance(e.get("data"), dict) else {}
                cond = edata.get("condition") if isinstance(edata.get("condition"), dict) else {}
                cond_prompt = _s(cond.get("prompt"))
                cond_type = _s(cond.get("type")) or "ai"
                if cond_prompt:
                    desc = (
                        f"if this expression is true: {cond_prompt}"
                        if cond_type == "logic"
                        else f'if "{cond_prompt}"'
                    )
                else:
                    desc = "otherwise (always)"
                lines.append(f"    → go to '{tgt}' {desc}")
        elif ntype not in ("endCall", "transferCall"):
            lines.append("- Next: end the conversation politely.")

    return "\n".join(lines).strip()
