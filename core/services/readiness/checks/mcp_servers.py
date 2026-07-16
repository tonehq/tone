"""Attached MCP servers — configured (shallow) + reachable (deep).

Per-resource sub-checks. A broken MCP server means only that server's tools
are unavailable — the agent still runs — so WARNING severity throughout.

Deep-probe reuses the same code that backs ``POST /mcp-server/validate_mcp_server``
to avoid duplicating transport-specific error handling.
"""

from __future__ import annotations

from typing import ClassVar, List

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    ShallowCheck,
    with_timeout,
)
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class McpServersConfiguredCheck(ShallowCheck):
    """Every attached MCP server must have a URL and be active."""

    id: ClassVar[str] = "mcp_servers.configured"
    category: ClassVar[Category] = Category.MCP_SERVERS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.mcp_servers)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No MCP servers attached."

    async def run(self, ctx: CheckContext) -> CheckResult:
        misconfigured = [
            s for s in ctx.mcp_servers
            if not (s.server_url or "").strip() or not s.is_active
        ]
        if misconfigured:
            names = ", ".join(s.name for s in misconfigured[:3])
            return self._fail(
                f"MCP server(s) misconfigured: {names}.",
                remediation="Open the MCP Servers page and fix or detach them.",
                resource_ref=ResourceRef(
                    type="mcp_server", id=str(misconfigured[0].id)
                ),
            )
        return self._pass(f"{len(ctx.mcp_servers)} MCP server(s) attached.")


class McpServerReachableCheck(DeepCheck):
    """Live-probe every attached MCP server via the same code path that backs
    ``POST /mcp-server/validate_mcp_server``."""

    id: ClassVar[str] = "mcp_servers.reachable"
    category: ClassVar[Category] = Category.MCP_SERVERS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.mcp_servers)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No MCP servers to probe."

    @with_timeout(5.0)  # slightly higher — MCP is often self-hosted and slow
    async def run(self, ctx: CheckContext) -> CheckResult:
        from fastapi import HTTPException

        from core.services.mcp_server_service import McpServerService

        svc = McpServerService(ctx.db, org_id=ctx.org_id)
        failed: List[str] = []
        for server in ctx.mcp_servers:
            try:
                await svc.validate_mcp_connection(
                    server_url=server.server_url,
                    transport_type=server.transport_type,
                    auth_config=server.auth_config,
                    auth_type=server.auth_type,
                )
            except HTTPException as exc:
                failed.append(f"'{server.name}': {exc.detail}")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"'{server.name}': {exc}")
        if failed:
            joined = "; ".join(failed[:2])
            more = f"; +{len(failed) - 2} more" if len(failed) > 2 else ""
            return self._fail(
                f"MCP server probe failed: {joined}{more}",
                remediation="Verify each MCP server's URL, transport, and credentials.",
            )
        return self._pass(f"All {len(ctx.mcp_servers)} MCP server(s) reachable.")
