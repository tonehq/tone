"""Attached tools — each linked tool must be usable + reachable.

Two checks:

* :class:`ToolsUsableCheck` (shallow) — structural: attached, active, has a URL
  for custom HTTP tools.
* :class:`ToolReachableCheck` (deep) — combines two flows:

  - **OAuth-connection probe** for every OAuth-linked tool (custom OR
    built-in like ``google_calendar`` / ``hubspot``): validates provider-match
    + scopes + performs a live token resolution (refreshing an expired token
    against the provider's token endpoint). Catches revoked scopes, expired
    refresh tokens, wrong-provider misconfigurations, and decrypt failures.
  - **HTTP GET probe** for active custom HTTP tools whose ``method`` is
    ``GET``: fires a live request using the runtime auth resolution.
    Write-method tools (POST/PUT/PATCH/DELETE) are skipped to avoid
    side-effects (booking, charging, deleting, …).

Both are ``WARNING``: one broken tool doesn't fail the whole agent — the call
still runs, just that tool call won't work.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from loguru import logger

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
from core.utils.auth_types import AUTH_TYPE_OAUTH, normalize_auth_type


# Probe timeout — same value the existing MCP deep check uses so the two
# deep-check families behave consistently under a slow network.
_PROBE_TIMEOUT_S = 5.0


def _url_shape_problem(url: Optional[str]) -> Optional[str]:
    """Return a short reason string when ``url`` is unusable for an HTTP tool,
    or ``None`` when the URL is well-formed enough to probe.

    Zero-I/O — pure string parsing. Catches typos (missing scheme, wrong
    scheme like ``htps://``, empty host) that would otherwise sail through the
    shallow check and only fail during the deep GET probe or a live call.
    """
    if not (url or "").strip():
        return "no URL"
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return "malformed URL"
    if parsed.scheme not in ("http", "https"):
        return "URL scheme must be http/https"
    if not parsed.netloc:
        return "URL missing host"
    return None


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
            # Custom HTTP tools need a well-formed URL; MCP tools ride the MCP
            # server so they don't carry a URL of their own.
            if t.tool_type == "custom":
                url_problem = _url_shape_problem(t.url)
                if url_problem is not None:
                    broken.append(f"'{t.name}' ({url_problem})")
        if broken:
            joined = ", ".join(broken[:3])
            more = f" and {len(broken) - 3} more" if len(broken) > 3 else ""
            return self._fail(
                f"Tool(s) not usable: {joined}{more}.",
                remediation="Open the Tools tab and fix or detach them.",
            )
        return self._pass(f"{len(ctx.tools)} tool(s) attached.")


class ToolReachableCheck(DeepCheck):
    """Live-probe every attached, active tool the way runtime would.

    Two flows share this check because they answer complementary halves of
    "will this tool work at call time?":

    * **OAuth-connection probe** — for every active tool that carries an
      ``oauth_connection_id`` (custom OR built-in like ``google_calendar`` /
      ``hubspot``), validate provider-match + scopes, then resolve the
      connection's Authorization header. Resolution is a real network call
      to the provider's token endpoint if the token is expired, so this
      catches revoked scopes, expired refresh tokens, decrypt failures,
      and wrong-provider misconfigurations up-front.
    * **HTTP GET probe** — for active custom HTTP tools whose method is
      ``GET``, additionally fire a live request using the same auth the
      runtime pipeline builds. Write-method tools (POST/PUT/PATCH/DELETE)
      are skipped to avoid side-effects (booking, charging, deleting, …).

    MCP-sourced tools (``tool_type == 'mcp'``) are skipped — they're covered
    by the MCP checks. Success criterion for the HTTP probe is **strict
    2xx**. All failure modes aggregate into a single ``FAIL`` naming the
    offending tools.
    """

    id: ClassVar[str] = "tools.reachable"
    category: ClassVar[Category] = Category.TOOLS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return any(self._needs_check(t) for t in ctx.tools)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No probeable or OAuth-linked tools attached."

    @with_timeout(_PROBE_TIMEOUT_S)
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.oauth_service import OAuthService
        from core.services.tool_service import ToolService

        tool_svc = ToolService(ctx.db, org_id=ctx.org_id)
        oauth_svc = OAuthService(ctx.db, org_id=ctx.org_id)

        failed: List[Tuple[str, str]] = []  # (tool_name, reason)
        first_failed_id: Optional[str] = None
        checked = 0

        # One client, reused across probes for connection pooling. Runtime
        # tool calls don't follow redirects — match that so "URL moved" fails
        # here rather than silently succeeding.
        async with httpx.AsyncClient(
            timeout=_PROBE_TIMEOUT_S, follow_redirects=False
        ) as client:
            for tool in ctx.tools:
                if not self._needs_check(tool):
                    continue
                checked += 1

                # 1) OAuth-connection probe. If a linked connection is broken
                #    the tool is guaranteed to fail at call time, so we skip
                #    the HTTP probe to avoid a redundant confusing 401.
                if self._has_oauth_connection(tool):
                    reason = self._probe_oauth(tool, tool_svc, oauth_svc)
                    if reason is not None:
                        failed.append((tool.name, reason))
                        if first_failed_id is None:
                            first_failed_id = str(tool.id)
                        continue

                # 2) HTTP GET probe for probeable custom tools.
                if self._is_probeable(tool):
                    reason = await self._probe_tool(client, tool)
                    if reason is not None:
                        failed.append((tool.name, reason))
                        if first_failed_id is None:
                            first_failed_id = str(tool.id)

        if failed:
            joined = "; ".join(f"'{n}': {r}" for n, r in failed[:2])
            more = f"; +{len(failed) - 2} more" if len(failed) > 2 else ""
            return self._fail(
                f"Tool probe failed: {joined}{more}",
                remediation=(
                    "Open the Tools tab and verify the URL, credentials, "
                    "linked connection, and any custom headers for each "
                    "failing tool."
                ),
                resource_ref=ResourceRef(type="tool", id=first_failed_id) if first_failed_id else None,
            )
        return self._pass(f"All {checked} tool(s) reachable.")

    # ── helpers ─────────────────────────────────────────────────────────────

    @classmethod
    def _needs_check(cls, tool) -> bool:
        """A tool needs this check iff it's active, not MCP-sourced, and
        either has an OAuth connection to validate or is a probeable HTTP
        GET target."""
        if not tool.is_active or tool.tool_type == "mcp":
            return False
        return cls._has_oauth_connection(tool) or cls._is_probeable(tool)

    @staticmethod
    def _has_oauth_connection(tool) -> bool:
        """True when a tool carries an effective OAuth connection (per-version
        override → entity default, see ``core.utils.oauth_resolution``)."""
        from core.utils.oauth_resolution import effective_of

        return effective_of(tool) is not None

    @staticmethod
    def _is_probeable(tool) -> bool:
        """A tool is probeable iff it's an active custom HTTP tool with a URL
        and a GET method. Write methods are skipped to avoid side-effects."""
        if not tool.is_active or tool.tool_type != "custom":
            return False
        if not (tool.url or "").strip():
            return False
        return (tool.method or "GET").upper() == "GET"

    @staticmethod
    def _probe_oauth(tool, tool_svc, oauth_svc) -> Optional[str]:
        """Validate the tool's OAuth connection the way runtime would use it:
        provider-match + scopes + live token resolution (refresh if expired).
        Returns ``None`` on success or a short reason on failure. Never
        raises — every failure mode maps to a message.

        Unlike ``custom_tool_service._resolve_connection_header`` which
        fail-opens at call time so the LLM can react to the resulting 401,
        this path surfaces the failure so the operator sees "reconnect
        Google Calendar" instead of silently degraded behavior.
        """
        from fastapi import HTTPException

        from core.utils.oauth_resolution import effective_of

        oauth_id = effective_of(tool)
        if not oauth_id:
            return None
        try:
            tool_svc._validate_oauth_provider_match(
                tool.app_integration_id, oauth_id
            )
            tool_svc._validate_oauth_scopes(tool.tool_type, oauth_id)
            connection = oauth_svc.get_connection(oauth_id)
            # Live token resolution: refresh if expired, mint if
            # client-credentials, decrypt if bearer/api-key. Any provider-
            # side failure (revoked refresh token, decrypt error, missing
            # key) raises here.
            oauth_svc.resolve_connection_auth_header(connection)
        except HTTPException as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                return str(detail.get("message") or detail)
            return str(detail)
        except Exception as exc:  # noqa: BLE001
            return str(exc)
        return None

    async def _probe_tool(self, client: httpx.AsyncClient, tool) -> Optional[str]:
        """Return ``None`` on success, or a short human-readable reason on
        failure. Never raises — every failure mode maps to a message."""
        try:
            headers = self._build_headers(tool)
        except Exception as exc:  # noqa: BLE001 — decrypt / OAuth resolver failure
            return f"credential resolution failed ({exc})"

        try:
            response = await client.get(tool.url, headers=headers)
        except httpx.RequestError as exc:
            # DNS, connection refused, TLS handshake — the tool URL is not
            # reachable. Bubble the exception class since messages differ across
            # httpx versions.
            return f"unreachable ({exc.__class__.__name__})"

        if 200 <= response.status_code < 300:
            return None
        if response.status_code in (401, 403):
            return f"auth rejected ({response.status_code})"
        return f"HTTP {response.status_code}"

    def _build_headers(self, tool) -> dict:
        """Assemble outbound HTTP headers exactly the way runtime does.

        Reuses :func:`build_auth_headers` (shared with MCP) for
        bearer / api_key / basic + custom headers, then layers the resolved
        OAuth Authorization header on top for OAuth-typed tools.
        """
        # Local imports keep this module import-cheap and avoid circulars.
        from core.services.custom_tool_service import _resolve_connection_header
        from core.services.mcp_server_service import build_auth_headers
        from core.services.tool_service import decrypt_auth_config

        decrypted = decrypt_auth_config(tool.auth_config)
        headers = build_auth_headers(
            decrypted,
            already_decrypted=True,
            auth_type=tool.auth_type,
        )

        if normalize_auth_type(tool.auth_type) == AUTH_TYPE_OAUTH:
            resolved = _resolve_connection_header(tool)
            if resolved is not None:
                header_name, header_value = resolved
                headers[header_name] = header_value
            else:
                # Match runtime behavior: swallow, log, fall through — the
                # request goes out without an Authorization header. The probe
                # will then get a 401 which is the *right* signal (auth is
                # broken), so we don't fail here.
                logger.warning(
                    "[readiness] OAuth resolution returned no header for tool '{}'",
                    tool.name,
                )

        return headers
