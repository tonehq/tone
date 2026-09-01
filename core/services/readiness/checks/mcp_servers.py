"""Attached MCP servers — configured (shallow) + reachable (deep).

A broken MCP server means only that server's tools are unavailable — the agent
still runs — so WARNING severity throughout.

**One message per server.** Every check here emits at most **one drawer row per
MCP server**, in plain language, so a user with two broken servers sees exactly
two messages (not one confusing joined string, and not the same server repeated
under four different technical checks). To keep that promise:

* :class:`McpServersConfiguredCheck` (shallow) owns the *static* problems —
  a server with no URL or one that's turned off. It reports those per server.
* :class:`McpServerReachableCheck` (deep) owns *connectivity* — it first checks
  the server responds at all, then completes the full MCP handshake (transport +
  auth + ``list_tools``). It **skips** any server the configured check already
  flagged, so no server is reported twice. It reuses the same code that backs
  ``POST /mcp-server/validate_mcp_server`` so transport-specific error handling
  isn't duplicated.

The two deep concerns (is the box up? does MCP work?) used to be two separate
checks that both reported the same down server — merging them here is what
removes that duplication.
"""

from __future__ import annotations

import contextlib
from typing import Any, AsyncIterator, ClassVar, Iterable, Optional, Tuple

import httpx
from loguru import logger

from core.services.readiness.base import CheckContext, DeepCheck, ShallowCheck
from core.services.readiness.checks._messages import oauth_failure_reason, quote
from core.services.readiness.checks._oauth_expiry import OAuthTokenExpiryShallowCheck
from core.services.readiness.checks._per_resource import (
    PerResourceCheck,
    ResourceProblem,
)
from core.services.readiness.schemas import Category, Severity


# Per-server probe budget. MCP servers are often self-hosted and slow to warm.
# Servers are probed concurrently (see ``run``), so this bounds the slowest
# single server, not the sum across all of them.
_PROBE_TIMEOUT_S = 5.0
# Overall budget for the whole deep check. Generous because each server does a
# cheap HTTP GET *then* the full handshake sequentially; servers run in
# parallel, so this is ~one server's worst case plus headroom.
_DEEP_TIMEOUT_S = 12.0


def _is_statically_broken(server: Any) -> Optional[str]:
    """Return a plain-English reason when a server can't be probed at all
    (no URL / turned off), or ``None`` when it's worth a live probe.

    Shared by the shallow configured check (which reports it) and the deep
    reachable check (which skips it) so a server is never reported twice.
    """
    if not (server.server_url or "").strip():
        return "no server URL is set"
    if not server.is_active:
        return "the server is turned off"
    return None


class McpServersConfiguredCheck(PerResourceCheck, ShallowCheck):
    """Static configuration of each attached MCP server — one row per server
    that's missing a URL or turned off. Everything else passes."""

    id: ClassVar[str] = "mcp_servers.configured"
    category: ClassVar[Category] = Category.MCP_SERVERS
    severity: ClassVar[Severity] = Severity.WARNING
    resource_ref_type: ClassVar[str] = "mcp_server"

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.mcp_servers)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No MCP servers attached."

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        return ctx.mcp_servers

    def _summary_message(self, count: int) -> str:
        return f"{count} MCP server(s) configured."

    async def _check_one(
        self, ctx: CheckContext, server: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        reason = _is_statically_broken(server)
        if reason is None:
            return None
        return ResourceProblem(
            f"{quote(server.name)} can't be used — {reason}.",
            remediation="Open the MCP Servers page to fix or remove it.",
        )


class McpServerOAuthTokenValidCheck(OAuthTokenExpiryShallowCheck):
    """Warn when any attached MCP server's linked OAuth token has expired.

    Distinct from the reachable-deep check so the failure is visible in
    the agent-list badge (shallow-only) and doesn't wait for the Deep
    rate limiter to release. See ``_oauth_expiry.py`` for the shared logic.
    """

    id: ClassVar[str] = "mcp_servers.oauth_token_valid"
    category: ClassVar[Category] = Category.MCP_SERVERS
    severity: ClassVar[Severity] = Severity.WARNING
    resource_type_ref: ClassVar[str] = "mcp_server"
    resource_display: ClassVar[str] = "MCP server"

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        # Inactive / URL-less servers won't be called, so an expired token on
        # one is noise — ``McpServersConfiguredCheck`` already flags that state.
        return [s for s in ctx.mcp_servers if _is_statically_broken(s) is None]


class McpServerReachableCheck(PerResourceCheck, DeepCheck):
    """Live-probe every attached MCP server and report one plain-English row
    per unreachable / misbehaving server.

    Per server: first a bare HTTP GET (is the box up at all?), then the full
    MCP handshake via the same code path that backs
    ``POST /mcp-server/validate_mcp_server``. Splitting the two lets the message
    say "we couldn't reach it" vs "it's up but the connection failed" instead of
    a confusing handshake error for a server that's simply offline.

    Servers the shallow configured check already flagged (no URL / turned off)
    are skipped so nothing is reported twice.
    """

    id: ClassVar[str] = "mcp_servers.reachable"
    category: ClassVar[Category] = Category.MCP_SERVERS
    severity: ClassVar[Severity] = Severity.WARNING
    resource_ref_type: ClassVar[str] = "mcp_server"
    probe_timeout: ClassVar[float] = _DEEP_TIMEOUT_S

    def applies(self, ctx: CheckContext) -> bool:
        return any(_is_statically_broken(s) is None for s in ctx.mcp_servers)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No reachable MCP servers to probe."

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        # Only probe servers that are statically OK; the configured check owns
        # the rest, so nothing is reported twice.
        return [s for s in ctx.mcp_servers if _is_statically_broken(s) is None]

    def _summary_message(self, count: int) -> str:
        return f"All {count} MCP server(s) are reachable."

    def _timeout_message(self, count: int) -> str:
        return "Couldn't reach some MCP servers in time — they may be slow. Run the check again."

    @contextlib.asynccontextmanager
    async def _shared(self, ctx: CheckContext) -> AsyncIterator[Any]:
        """One MCP service + pooled HTTP client, reused across all servers."""
        from core.services.mcp_server_service import McpServerService

        svc = McpServerService(ctx.db, org_id=ctx.org_id)
        async with httpx.AsyncClient(
            timeout=_PROBE_TIMEOUT_S, follow_redirects=True
        ) as client:
            yield (svc, client)

    async def _check_one(
        self, ctx: CheckContext, server: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        svc, client = shared
        reachable, unreachable_reason = await self._http_reachable(svc, client, server)
        if not reachable:
            return ResourceProblem(
                f"Can't reach {quote(server.name)} — {unreachable_reason}.",
                remediation=(
                    "Check the server's URL and that it's online, then run the "
                    "check again."
                ),
            )
        handshake_reason = await self._handshake(svc, server)
        if handshake_reason is not None:
            return ResourceProblem(
                f"{quote(server.name)} responded, but the connection failed — "
                f"{handshake_reason}.",
                remediation=(
                    "Check the server's transport type and credentials, or "
                    "reconnect its account, then run the check again."
                ),
            )
        return None

    async def _http_reachable(
        self, svc: Any, client: httpx.AsyncClient, server: Any
    ) -> Tuple[bool, Optional[str]]:
        """L4 reachability — a bare HTTP GET. MCP servers speak SSE / streaming
        HTTP, so 405 / 406 / 501 to a plain GET is fine; **any** response proves
        the box is up. Only a transport-level error (DNS, refused, timeout) or a
        failure building the request counts as unreachable.

        Returns ``(True, None)`` when up, or ``(False, reason)`` when not.
        """
        from core.services.mcp_server_service import (
            build_auth_headers,
            headers_from_meta,
        )
        from core.utils.oauth_resolution import effective_of

        url = (server.server_url or "").strip()
        try:
            # Mirror the runtime request shape: static auth_config headers, plus
            # custom meta_data headers, plus the OAuth-connection-resolved
            # Authorization header. Agent-version OAuth override wins over the
            # entity default — same precedence the pipeline uses.
            effective_oauth_id = effective_of(server)
            headers = {
                **build_auth_headers(server.auth_config, auth_type=server.auth_type),
                **headers_from_meta(server.meta_data),
                **svc._resolve_oauth_headers(effective_oauth_id),
            }
            await client.get(url, headers=headers)
            return True, None
        except httpx.RequestError:
            # DNS failure, connection refused, TLS error, timeout, etc. The
            # exception class name is noise to end users — say what it means.
            return False, "the server didn't respond"
        except Exception:  # noqa: BLE001 — header build / decrypt / OAuth resolve
            # Expected control-flow: a bad config/decrypt is exactly what
            # readiness surfaces. Log for debugging; never leak the raw error.
            logger.debug(
                "[readiness] MCP request-prep failed for server {}", server.name
            )
            return False, "its credentials couldn't be prepared"

    async def _handshake(self, svc: Any, server: Any) -> Optional[str]:
        """Full MCP handshake (transport + auth + ``list_tools``). Returns a
        short plain-English reason on failure, or ``None`` when it succeeds."""
        from fastapi import HTTPException

        from core.services.mcp_server_service import headers_from_meta
        from core.services.tool_service import decrypt_auth_config
        from core.utils.oauth_resolution import effective_of

        try:
            effective_oauth_id = effective_of(server)
            # A linked OAuth connection whose scopes were revoked in the
            # provider's dashboard still resolves to a valid token — the MCP
            # handshake would pass and only the actual tool call would fail.
            # Validate scopes + provider match up-front (in-memory, no I/O) so
            # revocation / wrong-provider surfaces here, not mid-conversation.
            svc._validate_oauth_provider_match(
                server.app_integration_id, effective_oauth_id
            )
            svc._validate_oauth_scopes(effective_oauth_id)
            # Mirror the runtime path (McpServerService.discover_tools): decrypt
            # the stored auth_config, then layer the custom meta_data headers and
            # the OAuth-resolved Authorization header on top via ``extra_headers``.
            decrypted_auth = decrypt_auth_config(server.auth_config)
            extra_headers = {
                **headers_from_meta(server.meta_data),
                **svc._resolve_oauth_headers(effective_oauth_id),
            }
            await svc.validate_mcp_connection(
                server_url=server.server_url,
                transport_type=server.transport_type,
                auth_config=decrypted_auth,
                extra_headers=extra_headers,
                auth_type=server.auth_type,
            )
            return None
        except HTTPException as exc:
            # ``detail`` is a deliberately user-facing validation message from
            # the MCP service — safe to surface. ``oauth_failure_reason`` maps
            # token/scope errors to a clean "reconnect" clause and falls back
            # to a humanized version for transport errors.
            return oauth_failure_reason(exc.detail)
        except Exception:  # noqa: BLE001
            # Unexpected error — log for debugging, but never surface the raw
            # exception text (may contain internal detail) to the user.
            logger.debug(
                "[readiness] MCP handshake unexpected error for server {}",
                server.name,
            )
            return "the connection couldn't be established"
