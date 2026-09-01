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

import contextlib
from typing import Any, AsyncIterator, ClassVar, Iterable, Optional
from urllib.parse import urlparse

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
        return "it has no URL"
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return "its URL is malformed"
    if parsed.scheme not in ("http", "https"):
        return "its URL must start with http:// or https://"
    if not parsed.netloc:
        return "its URL has no host"
    return None


class ToolsUsableCheck(PerResourceCheck, ShallowCheck):
    """Every attached tool must exist, be active, and (for HTTP tools) have a URL."""

    id: ClassVar[str] = "tools.usable"
    category: ClassVar[Category] = Category.TOOLS
    severity: ClassVar[Severity] = Severity.WARNING
    resource_ref_type: ClassVar[str] = "tool"

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.tools)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No tools attached to this agent version."

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        return ctx.tools

    def _summary_message(self, count: int) -> str:
        return f"{count} tool(s) attached."

    async def _check_one(
        self, ctx: CheckContext, tool: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        reason: Optional[str] = None
        if not tool.is_active:
            reason = "it's turned off"
        # Custom HTTP tools need a well-formed URL; MCP tools ride the MCP
        # server so they don't carry a URL of their own.
        elif tool.tool_type == "custom":
            reason = _url_shape_problem(tool.url)
        if reason is None:
            return None
        return ResourceProblem(
            f"{quote(tool.name)} can't be used — {reason}.",
            remediation="Open the Tools tab to fix or remove it.",
        )


class ToolOAuthTokenValidCheck(OAuthTokenExpiryShallowCheck):
    """Warn when any attached tool's linked OAuth token has expired.

    Applies to both custom OAuth-authed tools and built-ins that carry an
    ``oauth_connection_id`` (google_calendar, hubspot, …). Complements
    ``ToolReachableCheck`` (deep) by surfacing the same failure without
    a network call — see ``_oauth_expiry.py`` for the shared logic.
    """

    id: ClassVar[str] = "tools.oauth_token_valid"
    category: ClassVar[Category] = Category.TOOLS
    severity: ClassVar[Severity] = Severity.WARNING
    resource_type_ref: ClassVar[str] = "tool"
    resource_display: ClassVar[str] = "tool"

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        # Inactive tools won't be called, and MCP-sourced tools are covered
        # by the MCP-side check — no need to warn twice.
        return [t for t in ctx.tools if t.is_active and t.tool_type != "mcp"]


class ToolReachableCheck(PerResourceCheck, DeepCheck):
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
    resource_ref_type: ClassVar[str] = "tool"
    probe_timeout: ClassVar[float] = _PROBE_TIMEOUT_S

    def applies(self, ctx: CheckContext) -> bool:
        return any(self._needs_check(t) for t in ctx.tools)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No probeable or OAuth-linked tools attached."

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        return [t for t in ctx.tools if self._needs_check(t)]

    def _summary_message(self, count: int) -> str:
        return f"All {count} tool(s) reachable."

    def _timeout_message(self, count: int) -> str:
        return "Couldn't reach some tools in time — they may be slow. Run the check again."

    @contextlib.asynccontextmanager
    async def _shared(self, ctx: CheckContext) -> AsyncIterator[Any]:
        """Tool + OAuth services and a pooled HTTP client, reused per tool.
        Runtime tool calls don't follow redirects — match that so "URL moved"
        fails here rather than silently succeeding."""
        from core.services.oauth_service import OAuthService
        from core.services.tool_service import ToolService

        tool_svc = ToolService(ctx.db, org_id=ctx.org_id)
        oauth_svc = OAuthService(ctx.db, org_id=ctx.org_id)
        async with httpx.AsyncClient(
            timeout=_PROBE_TIMEOUT_S, follow_redirects=False
        ) as client:
            yield (tool_svc, oauth_svc, client)

    async def _check_one(
        self, ctx: CheckContext, tool: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        tool_svc, oauth_svc, client = shared
        reason: Optional[str] = None

        # 1) OAuth-connection probe. If a linked connection is broken the tool is
        #    guaranteed to fail at call time, so we skip the HTTP probe to avoid
        #    a redundant confusing 401.
        if self._has_oauth_connection(tool):
            oauth_reason = self._probe_oauth(tool, tool_svc, oauth_svc)
            if oauth_reason is not None:
                reason = oauth_failure_reason(oauth_reason)
        # 2) HTTP GET probe for probeable custom tools — runs when the OAuth
        #    check passed (or the tool has no OAuth connection).
        if reason is None and self._is_probeable(tool):
            reason = await self._probe_tool(client, tool)

        if reason is None:
            return None
        return ResourceProblem(
            f"{quote(tool.name)} can't be used — {reason}.",
            remediation=(
                "Open the Tools tab and check its URL, credentials, and "
                "linked connection."
            ),
        )

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
            # ``detail`` is a deliberately user-facing validation message from
            # the tool/OAuth service — safe to surface.
            detail = exc.detail
            if isinstance(detail, dict):
                return str(detail.get("message") or detail)
            return str(detail)
        except Exception:  # noqa: BLE001
            # Unexpected error — log for debugging, but never surface the raw
            # exception text (may contain internal detail) to the user.
            logger.debug(
                "[readiness] tool OAuth probe unexpected error for tool '{}'",
                tool.name,
            )
            return "its connection couldn't be verified"
        return None

    async def _probe_tool(self, client: httpx.AsyncClient, tool) -> Optional[str]:
        """Return ``None`` on success, or a short human-readable reason on
        failure. Never raises — every failure mode maps to a message."""
        try:
            headers = self._build_headers(tool)
        except Exception:  # noqa: BLE001 — decrypt / OAuth resolver failure
            logger.debug(
                "[readiness] tool credential prep failed for tool '{}'", tool.name
            )
            return "its credentials couldn't be prepared"

        try:
            response = await client.get(tool.url, headers=headers)
        except httpx.RequestError:
            # DNS, connection refused, TLS handshake — the tool URL is not
            # reachable. The exception class name is noise to end users.
            return "the server didn't respond"

        if 200 <= response.status_code < 300:
            return None
        if response.status_code in (401, 403):
            return f"authentication was rejected (HTTP {response.status_code})"
        return f"the server returned HTTP {response.status_code}"

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
