"""The workflow state machine. Pure — the runner injects LLM-backed callbacks.

The engine never imports Pipecat or calls an LLM directly. The runner provides:

* ``navigator(node_id, ai_edges, context, user_text) -> Optional[target_node_id]`` —
  picks among AI (plain-language) edges, or returns None to stay.
* ``extractor(node_data, context, user_text) -> dict`` — fills the node's
  ``variableExtractionPlan`` variables from the conversation.

Both are optional; without them, AI edges fall back to the first unconditional edge and
extraction is skipped — so the engine is still usable/testable offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.services.pipeline.workflow.conditions import evaluate_logic
from core.services.pipeline.workflow.context import WorkflowCallContext
from core.services.pipeline.workflow.graph import RuntimeEdge, WorkflowGraphRuntime

Navigator = Callable[[str, List[RuntimeEdge], WorkflowCallContext, str], Optional[str]]
Extractor = Callable[[Dict[str, Any], WorkflowCallContext, str], Dict[str, Any]]

_VAR = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
_MAX_SETTLE = 25  # guard against router cycles
_DEFAULT_MAX_VISITS = 10  # per-node re-entry cap (overridable via node data.maxVisits)


def substitute(text: Optional[str], variables: Dict[str, Any]) -> str:
    if not text:
        return ""
    return _VAR.sub(lambda m: str(variables.get(m.group(1), m.group(0))), text)


@dataclass
class NodeDirective:
    """What the runner should do after the engine settles on a node."""

    node_id: str
    node_type: str
    system_prompt: str = ""          # global prompt + node prompt (persona prepended by runner)
    speak: Optional[str] = None      # firstMessage to TTS on entry
    end_call: bool = False
    run_tool: Optional[Dict[str, Any]] = None  # {toolId} or {tool:{type}}
    stay: bool = False               # loop condition unmet → re-prompt current node
    register_tools: List[str] = field(default_factory=list)


class WorkflowEngine:
    def __init__(
        self,
        graph: WorkflowGraphRuntime,
        context: WorkflowCallContext,
        navigator: Optional[Navigator] = None,
        extractor: Optional[Extractor] = None,
    ):
        self.graph = graph
        self.ctx = context
        self.navigator = navigator
        self.extractor = extractor

    # ── public API ──
    def start(self) -> NodeDirective:
        start_id = self.graph.start_id
        if not start_id:
            return NodeDirective(node_id="", node_type="", end_call=True)
        self._enter(start_id, "start")
        return self._settle()

    def on_user_turn(self, user_text: str) -> NodeDirective:
        cur = self.ctx.current_node_id
        if not cur:
            return self.start()
        data = self.graph.node_data(cur)

        # 1. variable extraction for the current node
        if data.get("variableExtractionPlan") and self.extractor:
            try:
                self.ctx.update_variables(self.extractor(data, self.ctx, user_text) or {})
            except Exception:
                pass

        # 2. global-node interrupts (logic enter-conditions)
        g = self._check_globals()
        if g:
            self._enter(g, "global")
            return self._settle(user_text)

        # 3. route from the current node
        nxt = self._route(cur, user_text)
        if nxt is None:
            return self._directive_for(cur, stay=True)
        if self._exceeds_visits(nxt):
            return self._end_directive()
        self._enter(nxt, "edge")
        return self._settle(user_text)

    def advance_after_action(self, user_text: str = "") -> NodeDirective:
        """Called by the runner after a tool/action node completes, to route onward."""
        cur = self.ctx.current_node_id
        if not cur:
            return self.start()
        nxt = self._route(cur, user_text)
        if nxt is None:
            return self._directive_for(cur, stay=True)
        if self._exceeds_visits(nxt):
            return self._end_directive()
        self._enter(nxt, "edge")
        return self._settle(user_text)

    # ── internals ──
    def _enter(self, node_id: str, reason: str) -> None:
        self.ctx.enter(node_id, self.graph.node_type(node_id), reason)

    def _max_visits(self, node_id: str) -> int:
        raw = (self.graph.node_data(node_id) or {}).get("maxVisits")
        try:
            return int(raw) if raw else _DEFAULT_MAX_VISITS
        except (TypeError, ValueError):
            return _DEFAULT_MAX_VISITS

    def _exceeds_visits(self, node_id: str) -> bool:
        """True once a node has been entered as many times as its cap allows — stops
        infinite re-prompt / cross-turn loops the per-pass _MAX_SETTLE guard can't catch."""
        return self.ctx.visits(node_id) >= self._max_visits(node_id)

    def _end_directive(self) -> NodeDirective:
        return NodeDirective(
            node_id=self.ctx.current_node_id or "", node_type="endCall", end_call=True
        )

    def _check_globals(self) -> Optional[str]:
        for gid in self.graph.global_ids:
            if gid == self.ctx.current_node_id:
                continue
            cond = (self.graph.node_data(gid) or {}).get("condition")
            if cond and evaluate_logic(cond, self.ctx.variables):
                return gid
        return None

    def _route(self, node_id: str, user_text: str) -> Optional[str]:
        edges = self.graph.outgoing(node_id)
        if not edges:
            return None
        # logic edges first (deterministic)
        for e in edges:
            if e.condition_type == "logic" and evaluate_logic(e.condition_prompt, self.ctx.variables):
                return e.target
        # ai edges via navigator
        ai_edges = [e for e in edges if e.condition_type == "ai"]
        if ai_edges and self.navigator:
            chosen = self.navigator(node_id, ai_edges, self.ctx, user_text)
            if chosen:
                return chosen
        # fall back to the first unconditional edge
        for e in edges:
            if not e.condition_prompt.strip():
                return e.target
        return None

    def _settle(self, user_text: str = "") -> NodeDirective:
        """Follow router/auto nodes until an interactive or action node is reached."""
        for _ in range(_MAX_SETTLE):
            cur = self.ctx.current_node_id
            if not cur:
                return NodeDirective(node_id="", node_type="", end_call=True)
            ntype = self.graph.node_type(cur)
            if ntype == "decision":
                nxt = self._route(cur, user_text)
                if nxt is None:
                    return self._directive_for(cur, stay=True)
                if self._exceeds_visits(nxt):
                    return self._end_directive()
                self._enter(nxt, "router")
                continue
            return self._directive_for(cur)
        # cycle guard → end gracefully
        return NodeDirective(node_id=self.ctx.current_node_id or "", node_type="", end_call=True)

    def _directive_for(self, node_id: str, stay: bool = False) -> NodeDirective:
        data = self.graph.node_data(node_id)
        ntype = self.graph.node_type(node_id)
        v = self.ctx.variables
        node_prompt = substitute(data.get("prompt"), v)
        global_prompt = substitute(self.graph.global_prompt, v)
        system_prompt = "\n\n".join(p for p in (global_prompt, node_prompt) if p)
        speak = substitute((data.get("messagePlan") or {}).get("firstMessage"), v) or None

        directive = NodeDirective(
            node_id=node_id,
            node_type=ntype,
            system_prompt=system_prompt,
            speak=None if stay else speak,
            stay=stay,
        )
        if stay:
            return directive

        if ntype == "endCall":
            directive.end_call = True
        elif ntype == "tool":
            if data.get("toolId"):
                directive.run_tool = {"toolId": data["toolId"]}
            elif data.get("tool"):
                directive.run_tool = {"tool": data["tool"]}
        elif ntype == "conversation":
            directive.register_tools = list(data.get("toolIds") or [])
        return directive
