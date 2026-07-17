"""Attached MCP servers — configured (shallow) + reachable (deep).

Per-resource sub-checks. A broken MCP server means only that server's tools
are unavailable — the agent still runs — so WARNING severity throughout.

Deep probes split the "is the server up?" question from the "does MCP work?"
question:

* :class:`McpServerHttpReachableCheck` — plain HTTP GET at ``server_url``.
  L4 reachability only; any response counts as up.
* :class:`McpServerReachableCheck` — full MCP handshake via
  :meth:`McpServerService.validate_mcp_connection` (transport + auth +
  ``list_tools``). Reuses the same code that backs
  ``POST /mcp-server/validate_mcp_server`` so transport-specific error
  handling isn't duplicated.
"""

from __future__ import annotations

from typing import ClassVar, List

import httpx

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


# Probe timeout — MCP servers are often self-hosted and slow to warm; matches
# the timeout the full-handshake probe uses below.
_PROBE_TIMEOUT_S = 5.0


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


class McpServerHttpReachableCheck(DeepCheck):
    """L4 reachability probe — plain HTTP GET against each server's URL.

    Runs BEFORE :class:`McpServerReachableCheck` in the registry so that if the
    server is simply unreachable at the network layer, the report attributes
    the failure to "server down" rather than "MCP handshake broken".

    MCP servers speak SSE or streaming HTTP; a bare ``GET`` legitimately
    returns 405 / 406 / 501 on many implementations. We treat **any HTTP
    response** as success — the signal we want is "did the box respond?", not
    "did it respond correctly". The strict MCP-level check next door is where
    protocol correctness is asserted.
    """

    id: ClassVar[str] = "mcp_servers.http_reachable"
    category: ClassVar[Category] = Category.MCP_SERVERS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.mcp_servers)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No MCP servers to probe."

    @with_timeout(_PROBE_TIMEOUT_S)
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.mcp_server_service import build_auth_headers

        failed: List[str] = []
        first_failed_id: str | None = None

        async with httpx.AsyncClient(
            timeout=_PROBE_TIMEOUT_S, follow_redirects=True
        ) as client:
            for server in ctx.mcp_servers:
                url = (server.server_url or "").strip()
                if not url:
                    failed.append(f"'{server.name}': missing URL")
                    if first_failed_id is None:
                        first_failed_id = str(server.id)
                    continue
                try:
                    headers = build_auth_headers(
                        server.auth_config, auth_type=server.auth_type
                    )
                    await client.get(url, headers=headers)
                except httpx.RequestError as exc:
                    failed.append(f"'{server.name}': unreachable ({exc.__class__.__name__})")
                    if first_failed_id is None:
                        first_failed_id = str(server.id)
                except Exception as exc:  # noqa: BLE001 — header build / decrypt
                    failed.append(f"'{server.name}': {exc}")
                    if first_failed_id is None:
                        first_failed_id = str(server.id)

        if failed:
            joined = "; ".join(failed[:2])
            more = f"; +{len(failed) - 2} more" if len(failed) > 2 else ""
            return self._fail(
                f"MCP server HTTP probe failed: {joined}{more}",
                remediation="Verify each MCP server's URL and network reachability.",
                resource_ref=ResourceRef(type="mcp_server", id=first_failed_id)
                if first_failed_id else None,
            )
        return self._pass(f"All {len(ctx.mcp_servers)} MCP server(s) responded to HTTP GET.")


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

    @with_timeout(_PROBE_TIMEOUT_S)
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
