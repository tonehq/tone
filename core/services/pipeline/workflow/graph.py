"""In-memory index over a canonical workflow graph for fast call-time traversal."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RuntimeEdge:
    id: str
    source: str
    target: str
    condition_type: str  # "ai" | "logic"
    condition_prompt: str


class WorkflowGraphRuntime:
    """Wraps the stored graph dict and exposes node/edge lookups by node id.

    Node ids equal the Vapi ``name``. Each node's domain fields live under ``data``.
    """

    def __init__(self, graph: Dict[str, Any]):
        self.graph = graph or {}
        self.global_prompt: str = self.graph.get("globalPrompt", "") or ""
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._out: Dict[str, List[RuntimeEdge]] = {}
        self._start_id: Optional[str] = None
        self._global_ids: List[str] = []
        self._index()

    def _index(self) -> None:
        for n in self.graph.get("nodes", []) or []:
            nid = n.get("id")
            if not nid:
                continue
            self._nodes[nid] = n
            data = n.get("data") or {}
            if data.get("isStart"):
                self._start_id = nid
            if data.get("isGlobal"):
                self._global_ids.append(nid)
            self._out.setdefault(nid, [])

        for e in self.graph.get("edges", []) or []:
            src = e.get("source")
            tgt = e.get("target")
            if not src or not tgt:
                continue
            cond = (e.get("data") or {}).get("condition") or {}
            self._out.setdefault(src, []).append(
                RuntimeEdge(
                    id=e.get("id", f"{src}->{tgt}"),
                    source=src,
                    target=tgt,
                    condition_type=cond.get("type", "ai"),
                    condition_prompt=cond.get("prompt", "") or "",
                )
            )

    # ── accessors ──
    def node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._nodes.get(node_id)

    def node_data(self, node_id: str) -> Dict[str, Any]:
        node = self._nodes.get(node_id) or {}
        return node.get("data") or {}

    def node_type(self, node_id: str) -> str:
        node = self._nodes.get(node_id) or {}
        return node.get("type", "")

    def outgoing(self, node_id: str) -> List[RuntimeEdge]:
        return self._out.get(node_id, [])

    @property
    def start_id(self) -> Optional[str]:
        return self._start_id

    @property
    def global_ids(self) -> List[str]:
        return list(self._global_ids)
