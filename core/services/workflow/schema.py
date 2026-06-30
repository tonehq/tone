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


class TransferCallData(_BaseNodeData):
    destination: Optional[Dict[str, Any]] = None
    transferPlan: Optional[Dict[str, Any]] = None
    messagePlan: Optional[MessagePlan] = None


class EndCallData(_BaseNodeData):
    messagePlan: Optional[MessagePlan] = None


class DecisionData(_BaseNodeData):
    prompt: Optional[str] = None


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


class TransferCallNode(_NodeBase):
    type: Literal["transferCall"]
    data: TransferCallData


class EndCallNode(_NodeBase):
    type: Literal["endCall"]
    data: EndCallData


class DecisionNode(_NodeBase):
    type: Literal["decision"]
    data: DecisionData


WorkflowNode = Annotated[
    Union[ConversationNode, ToolNode, TransferCallNode, EndCallNode, DecisionNode],
    Field(discriminator="type"),
]

TERMINAL_TYPES = {"endCall", "transferCall"}


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
        issues.append({"code": "EMPTY", "node_name": None, "message": "Workflow has no nodes."})
        return issues

    # 3. Exactly one start node.
    starts = [n for n in nodes if getattr(n.data, "isStart", False)]
    if len(starts) == 0:
        issues.append({"code": "NO_START", "node_name": None, "message": "No start node (set isStart on the entry node)."})
    elif len(starts) > 1:
        for n in starts:
            issues.append({"code": "MULTIPLE_START", "node_name": n.id, "message": "More than one start node."})

    id_set = set(ids)

    # 4. Edges reference existing nodes.
    for e in edges:
        if e.source not in id_set:
            issues.append({"code": "DANGLING_EDGE", "node_name": e.source, "message": f"Edge source '{e.source}' is not a node."})
        if e.target not in id_set:
            issues.append({"code": "DANGLING_EDGE", "node_name": e.target, "message": f"Edge target '{e.target}' is not a node."})

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
            issues.append({"code": "TERMINAL_OUTGOING", "node_name": n.id, "message": "Terminal node must not have outgoing edges."})
        if not is_terminal and out_map[n.id] == 0 and n.id not in global_ids:
            issues.append({"code": "DEAD_END", "node_name": n.id, "message": "Non-terminal node has no outgoing edge."})

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
                issues.append({"code": "UNREACHABLE", "node_name": nid, "message": "Node is not reachable from the start node."})

        # 7. At least one reachable terminal.
        if not any(type_map[nid] in TERMINAL_TYPES for nid in reachable if nid in type_map):
            issues.append({"code": "NO_TERMINAL", "node_name": None, "message": "No reachable End/Transfer node — the call can never end."})

    return issues


def find_start_node_name(graph: Dict[str, Any]) -> Optional[str]:
    for n in graph.get("nodes", []) or []:
        data = n.get("data") or {}
        if data.get("isStart"):
            return data.get("name") or n.get("id")
    return None
