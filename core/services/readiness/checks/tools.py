"""Attached tools — each linked tool must be usable + reachable.

Two checks:

* :class:`ToolsUsableCheck` (shallow) — structural: attached, active, has a URL
  for custom HTTP tools.
* :class:`ToolReachableCheck` (deep) — for custom tools whose ``method`` is
  ``GET``, fires a live request using the same auth resolution the runtime
  pipeline uses. Write-method tools (POST/PUT/PATCH/DELETE) are skipped to
  avoid side-effects (booking, charging, deleting, …).

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
    """Live-probe every attached, active, GET-method custom HTTP tool.

    Write-method tools are skipped (see module docstring). MCP-sourced tools are
    covered by the MCP checks. Success criterion is **strict 2xx** — anything
    else, or a network-level failure, aggregates into a single ``FAIL`` naming
    the offending tools.
    """

    id: ClassVar[str] = "tools.reachable"
    category: ClassVar[Category] = Category.TOOLS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return any(self._is_probeable(t) for t in ctx.tools)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No GET-method custom tools to probe."

    @with_timeout(_PROBE_TIMEOUT_S)
    async def run(self, ctx: CheckContext) -> CheckResult:
        targets = [t for t in ctx.tools if self._is_probeable(t)]
        failed: List[Tuple[str, str]] = []  # (tool_name, reason)
        first_failed_id: Optional[str] = None

        # One client, reused across probes for connection pooling. Runtime
        # tool calls don't follow redirects — match that so "URL moved" fails
        # here rather than silently succeeding.
        async with httpx.AsyncClient(
            timeout=_PROBE_TIMEOUT_S, follow_redirects=False
        ) as client:
            for tool in targets:
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
                    "Open the Tools tab and verify the URL, credentials, and "
                    "any custom headers for each failing tool."
                ),
                resource_ref=ResourceRef(type="tool", id=first_failed_id) if first_failed_id else None,
            )
        return self._pass(f"All {len(targets)} GET tool(s) reachable.")

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_probeable(tool) -> bool:
        """A tool is probeable iff it's an active custom HTTP tool with a URL
        and a GET method. Write methods are skipped to avoid side-effects."""
        if not tool.is_active or tool.tool_type != "custom":
            return False
        if not (tool.url or "").strip():
            return False
        return (tool.method or "GET").upper() == "GET"

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
