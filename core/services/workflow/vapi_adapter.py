"""Convert between the canonical React-Flow-native graph and Vapi's flat export shape.

Vapi shape: nodes keyed by ``name`` with fields at the top level + ``metadata.position``;
edges ``{from, to, condition}``. Canonical shape: nodes ``{id, type, position, data}``;
edges ``{id, source, target, data:{condition}}``. Used only by the import/export endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List


def from_vapi(vapi: Dict[str, Any]) -> Dict[str, Any]:
    """Vapi flat graph → canonical React-Flow-native graph."""
    nodes: List[Dict[str, Any]] = []
    for vn in vapi.get("nodes", []) or []:
        node = dict(vn)
        name = node.get("name") or node.get("id") or f"node_{len(nodes)}"
        node_type = node.pop("type", "conversation")
        metadata = node.pop("metadata", {}) or {}
        position = metadata.get("position") or {"x": 0, "y": 0}
        node.pop("id", None)
        data = dict(node)  # remaining fields are node data
        data["name"] = name
        nodes.append({
            "id": name,
            "type": node_type,
            "position": {"x": position.get("x", 0), "y": position.get("y", 0)},
            "data": data,
        })

    edges: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for ve in vapi.get("edges", []) or []:
        src = ve.get("from")
        tgt = ve.get("to")
        if not src or not tgt:
            continue
        cond = ve.get("condition") or {"type": "ai", "prompt": ""}
        base_id = f"{src}->{tgt}"
        edge_id = base_id
        i = 1
        while edge_id in seen_ids:
            edge_id = f"{base_id}#{i}"
            i += 1
        seen_ids.add(edge_id)
        edges.append({
            "id": edge_id,
            "source": src,
            "target": tgt,
            "type": "condition",
            "data": {"condition": cond},
        })

    return {
        "schemaVersion": vapi.get("schemaVersion", 1),
        "nodes": nodes,
        "edges": edges,
        "globalPrompt": vapi.get("globalPrompt", "") or "",
        "artifactPlan": vapi.get("artifactPlan"),
    }


def to_vapi(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical graph → Vapi flat export shape."""
    nodes: List[Dict[str, Any]] = []
    for n in graph.get("nodes", []) or []:
        data = dict(n.get("data") or {})
        name = data.pop("name", None) or n.get("id")
        position = n.get("position") or {"x": 0, "y": 0}
        vn: Dict[str, Any] = {"name": name, "type": n.get("type")}
        vn.update(data)
        vn["metadata"] = {"position": {"x": position.get("x", 0), "y": position.get("y", 0)}}
        nodes.append(vn)

    edges: List[Dict[str, Any]] = []
    for e in graph.get("edges", []) or []:
        cond = (e.get("data") or {}).get("condition") or {"type": "ai", "prompt": ""}
        edges.append({"from": e.get("source"), "to": e.get("target"), "condition": cond})

    out = {
        "nodes": nodes,
        "edges": edges,
        "globalPrompt": graph.get("globalPrompt", "") or "",
    }
    if graph.get("artifactPlan") is not None:
        out["artifactPlan"] = graph.get("artifactPlan")
    return out
