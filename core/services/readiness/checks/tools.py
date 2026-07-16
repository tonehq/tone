"""Attached tools — each linked tool must be usable.

Per-resource sub-check aggregated into one report row. One broken tool
doesn't fail the whole agent — the call still runs, just that tool call
won't work — so this stays WARNING severity.
"""

from __future__ import annotations

from typing import ClassVar, List

from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.schemas import Category, CheckResult, Severity


class ToolsUsableCheck(ShallowCheck):
    """Every attached tool must exist, be active, and (for HTTP tools) have a URL."""

    id: ClassVar[str] = "tools.usable"
    category: ClassVar[Category] = Category.TOOLS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.tools)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No tools attached to this agent version."

    async def run(self, ctx: CheckContext) -> CheckResult:
        broken: List[str] = []
        for t in ctx.tools:
            if not t.is_active:
                broken.append(f"'{t.name}' (disabled)")
                continue
            # Custom HTTP tools need a URL; MCP tools ride the MCP server.
            if t.tool_type == "custom" and not (t.url or "").strip():
                broken.append(f"'{t.name}' (no URL)")
        if broken:
            joined = ", ".join(broken[:3])
            more = f" and {len(broken) - 3} more" if len(broken) > 3 else ""
            return self._fail(
                f"Tool(s) not usable: {joined}{more}.",
                remediation="Open the Tools tab and fix or detach them.",
            )
        return self._pass(f"{len(ctx.tools)} tool(s) attached.")
