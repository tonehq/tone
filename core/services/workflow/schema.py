"""Pydantic models for the canonical workflow graph + a pure ``validate_graph``.

The persisted/canonical graph is **React-Flow-native** — each node is
``{id, type, position, data}`` and each edge ``{id, source, target, type, data}`` —
with the Vapi field set nested inside ``node.data`` and the routing condition inside
``edge.data.condition``. All data models allow extra keys for forward-compatibility.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.models.enums import EdgeConditionType


# ---------------------------------------------------------------------------
# Shared value objects
# ---------------------------------------------------------------------------

class XY(BaseModel):
    model_config = ConfigDict(extra="allow")
    x: float = 0.0
    y: float = 0.0


class MessagePlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    firstMessage: Optional[str] = None


class ExtractVar(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    type: str = "string"
    enum: List[str] = Field(default_factory=list)
    description: str = ""


class VariableExtractionPlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    output: List[ExtractVar] = Field(default_factory=list)


class InlineTool(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str  # e.g. "endCall", "transferCall", "sms"


# ---------------------------------------------------------------------------
# Per-node data (discriminated by the node's ``type`` at the node level)
# ---------------------------------------------------------------------------

class _BaseNodeData(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    isStart: bool = False
    isGlobal: bool = False
    # Enter-condition (LiquidJS) for a global node — routable from anywhere.
    condition: Optional[str] = None


class ConversationData(_BaseNodeData):
    prompt: Optional[str] = None
    messagePlan: Optional[MessagePlan] = None
    variableExtractionPlan: Optional[VariableExtractionPlan] = None
    toolIds: List[str] = Field(default_factory=list)
    # infinite-loop guard for re-prompting nodes
    maxVisits: int = 6


class ToolData(_BaseNodeData):
    toolId: Optional[str] = None
    mcpServerId: Optional[str] = None
    mcpToolName: Optional[str] = None
    tool: Optional[InlineTool] = None


class EndCallData(_BaseNodeData):
    messagePlan: Optional[MessagePlan] = None


class DecisionData(_BaseNodeData):
    prompt: Optional[str] = None


class KeyValueField(BaseModel):
    """A header or static-body entry. ``value`` may contain ``{{var}}`` templates.
    ``encrypt`` marks the value to be stored AES-encrypted in the graph at rest."""
    model_config = ConfigDict(extra="allow")
    key: str
    value: str = ""
    encrypt: bool = False


class RequestBodyProp(BaseModel):
    """A request-body property the LLM fills (becomes a tool parameter)."""
    model_config = ConfigDict(extra="allow")
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""


class ResponseField(BaseModel):
    """A field to extract from the JSON response (prompt-guided)."""
    model_config = ConfigDict(extra="allow")
    name: str
    type: str = "string"
    required: bool = False


class ResponseAlias(BaseModel):
    """Map a response field to a different workflow-variable name (prompt-guided)."""
    model_config = ConfigDict(extra="allow")
    responseField: str
    alias: str


class ApiMessages(BaseModel):
    model_config = ConfigDict(extra="allow")
    start: Optional[str] = None
    success: Optional[str] = None
    failed: Optional[str] = None
    delayed: Optional[str] = None


class ApiRequestData(_BaseNodeData):
    description: str = ""
    method: str = "GET"
    url: str = ""
    headers: List[KeyValueField] = Field(default_factory=list)
    requestBody: List[RequestBodyProp] = Field(default_factory=list)
    staticBody: List[KeyValueField] = Field(default_factory=list)
    responseFields: List[ResponseField] = Field(default_factory=list)
    aliases: List[ResponseAlias] = Field(default_factory=list)
    messages: Optional[ApiMessages] = None


# ---------------------------------------------------------------------------
# Nodes (discriminated union on ``type``)
# ---------------------------------------------------------------------------

class _NodeBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    position: XY = Field(default_factory=XY)


class ConversationNode(_NodeBase):
    type: Literal["conversation"]
    data: ConversationData


class ToolNode(_NodeBase):
    type: Literal["tool"]
    data: ToolData


class EndCallNode(_NodeBase):
    type: Literal["endCall"]
    data: EndCallData


class DecisionNode(_NodeBase):
    type: Literal["decision"]
    data: DecisionData


class ApiRequestNode(_NodeBase):
    type: Literal["apiRequest"]
    data: ApiRequestData


WorkflowNode = Annotated[
    Union[ConversationNode, ToolNode, EndCallNode, DecisionNode, ApiRequestNode],
    Field(discriminator="type"),
]

TERMINAL_TYPES = {"endCall"}


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

class EdgeCondition(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: EdgeConditionType = EdgeConditionType.AI
    prompt: str = ""


class EdgeData(BaseModel):
    model_config = ConfigDict(extra="allow")
    condition: EdgeCondition = Field(default_factory=EdgeCondition)


class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    source: str
    target: str
    type: str = "condition"
    data: EdgeData = Field(default_factory=EdgeData)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class WorkflowGraph(BaseModel):
    model_config = ConfigDict(extra="allow")
    schemaVersion: int = 1
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    globalPrompt: str = ""
    artifactPlan: Optional[Dict[str, Any]] = None


# Hard caps on untrusted graph size — bound parse/checksum/validation/storage cost.
MAX_NODES = 300
MAX_EDGES = 1000


def graph_size_error(graph: Dict[str, Any]) -> Optional[str]:
    """Return a human message if the graph exceeds node/edge caps, else None."""
    if not isinstance(graph, dict):
        return None
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if isinstance(nodes, list) and len(nodes) > MAX_NODES:
        return f"Workflow exceeds the maximum of {MAX_NODES} nodes."
    if isinstance(edges, list) and len(edges) > MAX_EDGES:
        return f"Workflow exceeds the maximum of {MAX_EDGES} edges."
    return None


def empty_graph(start_node_name: str = "start") -> Dict[str, Any]:
    """A minimal graph: a single Start conversation node. Not yet *valid* — it has no
    terminal/outgoing edge, so validate_graph reports DEAD_END/NO_TERMINAL until built out."""
    return {
        "schemaVersion": 1,
        "nodes": [
            {
                "id": start_node_name,
                "type": "conversation",
                "position": {"x": 0, "y": 0},
                "data": {
                    "name": start_node_name,
                    "isStart": True,
                    "prompt": "Greet the caller and ask how you can help.",
                    "messagePlan": {"firstMessage": "Hi! How can I help you today?"},
                },
            }
        ],
        "edges": [],
        "globalPrompt": "",
        "artifactPlan": None,
    }


# ---------------------------------------------------------------------------
# Validation (pure — returns a list of issues, never raises)
# ---------------------------------------------------------------------------

def validate_graph(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate a canonical graph. Returns ``[{code, node_name, message}]`` (empty == valid)."""
    issues: List[Dict[str, Any]] = []

    if not isinstance(graph, dict):
        return [{"code": "BAD_GRAPH", "node_name": None, "message": "Graph must be an object."}]

    # 0. Size cap — refuse to parse/validate an oversized graph.
    size_err = graph_size_error(graph)
    if size_err:
        return [{"code": "TOO_LARGE", "node_name": None, "message": size_err}]

    # 1. Parse against the typed model (per-type config validation).
    try:
        parsed = WorkflowGraph.model_validate(graph)
    except ValidationError as exc:
        for err in exc.errors()[:25]:
            loc = ".".join(str(p) for p in err.get("loc", ()))
            issues.append({"code": "INVALID_CONFIG", "node_name": loc, "message": err.get("msg", "invalid")})
        # Cannot run structural checks reliably on a malformed graph.
        return issues

    nodes = parsed.nodes
    edges = parsed.edges
    ids = [n.id for n in nodes]

    # 2. Unique node ids.
    seen = set()
    for nid in ids:
        if nid in seen:
            issues.append({"code": "DUPLICATE_ID", "node_name": nid, "message": f"Duplicate node id '{nid}'."})
        seen.add(nid)

    if not nodes:
        issues.append({"code": "EMPTY", "node_name": None, "message": "This workflow is empty. Add a Start node and at least one End Call node to begin."})
        return issues

    # 3. Exactly one start node.
    starts = [n for n in nodes if getattr(n.data, "isStart", False)]
    if len(starts) == 0:
        issues.append({"code": "NO_START", "node_name": None, "message": "No entry point set. Open the first node and turn on “Start” so the call knows where to begin."})
    elif len(starts) > 1:
        for n in starts:
            issues.append({"code": "MULTIPLE_START", "node_name": n.id, "message": "Two nodes are marked as Start. A workflow can have only one — turn off “Start” on all but the entry node."})

    id_set = set(ids)

    # 4. Edges reference existing nodes.
    for e in edges:
        if e.source not in id_set:
            issues.append({"code": "DANGLING_EDGE", "node_name": e.source, "message": f"A connection starts from '{e.source}', which no longer exists. Delete the connection and redraw it from a real node."})
        if e.target not in id_set:
            issues.append({"code": "DANGLING_EDGE", "node_name": e.target, "message": f"A connection points to '{e.target}', which no longer exists. Delete the connection and redraw it to a real node."})

    # 5. Terminal nodes have no outgoing; non-terminal nodes have outgoing (unless global).
    out_map: Dict[str, int] = {nid: 0 for nid in ids}
    for e in edges:
        if e.source in out_map:
            out_map[e.source] += 1
    type_map = {n.id: n.type for n in nodes}
    global_ids = {n.id for n in nodes if getattr(n.data, "isGlobal", False)}
    for n in nodes:
        is_terminal = n.type in TERMINAL_TYPES
        if is_terminal and out_map[n.id] > 0:
            issues.append({"code": "TERMINAL_OUTGOING", "node_name": n.id, "message": "An End Call node ends the call, so it can’t have outgoing connections. Remove the connections leaving this node."})
        if not is_terminal and out_map[n.id] == 0 and n.id not in global_ids:
            issues.append({"code": "DEAD_END", "node_name": n.id, "message": "This node has no outgoing connection, so the call gets stuck here. Draw a connection to the next step (or to an End Call node)."})

    _METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    for n in nodes:
        if n.type != "apiRequest":
            continue
        d = n.data
        url = (getattr(d, "url", "") or "").strip()
        if not url:
            issues.append({"code": "INVALID_URL", "node_name": n.id, "message": "This API Request node has no URL. Open it and enter the endpoint to call."})
        elif not (url.startswith("https://") or url.startswith("{{")):
            issues.append({"code": "INVALID_URL", "node_name": n.id, "message": "The API Request URL must start with https:// (or a {{variable}}). Update the URL to use a secure address."})
        if (getattr(d, "method", "GET") or "GET").upper() not in _METHODS:
            issues.append({"code": "INVALID_METHOD", "node_name": n.id, "message": "Unsupported HTTP method."})
        for label, rows, keyattr in (
            ("header", getattr(d, "headers", None) or [], "key"),
            ("static body field", getattr(d, "staticBody", None) or [], "key"),
            ("body property", getattr(d, "requestBody", None) or [], "name"),
        ):
            seen_keys = set()
            for row in rows:
                k = (getattr(row, keyattr, "") or "").strip()
                if k and k in seen_keys:
                    issues.append({"code": "DUPLICATE_KEY", "node_name": n.id, "message": f"Duplicate {label} '{k}'."})
                seen_keys.add(k)

    # 6. Reachability from start (global nodes are reachable by definition).
    if starts:
        adj: Dict[str, List[str]] = {nid: [] for nid in ids}
        for e in edges:
            if e.source in adj and e.target in id_set:
                adj[e.source].append(e.target)
        reachable = set(global_ids)
        stack = [starts[0].id]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            stack.extend(adj.get(cur, []))
        for nid in ids:
            if nid not in reachable:
                issues.append({"code": "UNREACHABLE", "node_name": nid, "message": "Nothing connects to this node, so the call can never reach it. Add an incoming connection from an earlier step, or delete the node."})

        # 7. At least one reachable terminal.
        if not any(type_map[nid] in TERMINAL_TYPES for nid in reachable if nid in type_map):
            issues.append({"code": "NO_TERMINAL", "node_name": None, "message": "The call can never end — no End Call node is reachable from Start. Add an End Call node and connect a path to it."})

    return issues


def find_start_node_name(graph: Dict[str, Any]) -> Optional[str]:
    for n in graph.get("nodes", []) or []:
        data = n.get("data") or {}
        if data.get("isStart"):
            return data.get("name") or n.get("id")
    return None
