"""Per-call mutable workflow state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraversalEntry:
    node_id: str
    node_type: str
    reason: str = ""
    variables_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowCallContext:
    """Holds the live state of one call's traversal through a workflow graph."""

    variables: Dict[str, Any] = field(default_factory=dict)
    current_node_id: Optional[str] = None
    history: List[TraversalEntry] = field(default_factory=list)
    visit_counts: Dict[str, int] = field(default_factory=dict)

    def enter(self, node_id: str, node_type: str, reason: str = "") -> None:
        self.current_node_id = node_id
        self.visit_counts[node_id] = self.visit_counts.get(node_id, 0) + 1
        self.history.append(
            TraversalEntry(
                node_id=node_id,
                node_type=node_type,
                reason=reason,
                variables_snapshot=dict(self.variables),
            )
        )

    def visits(self, node_id: str) -> int:
        return self.visit_counts.get(node_id, 0)

    def update_variables(self, values: Dict[str, Any]) -> None:
        for k, v in (values or {}).items():
            if v is not None:
                self.variables[k] = v

    def to_record(self) -> Dict[str, Any]:
        """Serialisable snapshot for the Call record (analytics/debugging)."""
        return {
            "variables": self.variables,
            "history": [
                {"node_id": h.node_id, "node_type": h.node_type, "reason": h.reason}
                for h in self.history
            ],
        }
