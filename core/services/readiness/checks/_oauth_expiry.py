"""Shared shallow-check base for OAuth-token expiry on attached resources.

Two resource families carry a linked ``OAuthConnection`` today: MCP servers
and Tools (custom HTTP + built-ins like google_calendar / hubspot). Both
suffer the same failure mode — a linked OAuth token quietly reaches
``token_expiry`` and the Deep probe that would refresh it is either
rate-limited or served from a stale snapshot. Both categories therefore
want a **cheap, DB-only shallow check** that surfaces the expiry the
moment shallow readiness runs (including the agent-list badge).

This module implements the check body once — expiry inspection, formatting,
skip logic — so ``mcp_servers.py`` and ``tools.py`` only declare a 6-line
subclass pinning their category, resource-type label, and context lookup.

Refresh / revocation *behavior* (does refresh work? did the provider revoke
scopes?) is out of scope here — those questions require a network call and
belong to the Deep checks. This check only asserts "the local expiry
timestamp says the token is still usable".
"""

from __future__ import annotations

import time
from abc import abstractmethod
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from core.models.oauth_connection import OAuthConnection
from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.schemas import CheckResult, ResourceRef
from core.utils.oauth_resolution import effective_of


# Same 60-second buffer used by ``OAuthService.get_valid_access_token_for_connection``
# (see ``core/services/oauth_service.py:572``). Keeping the two constants aligned
# means shallow and Deep agree on when a token counts as "about to expire".
_EXPIRY_BUFFER_SECONDS = 60


class OAuthTokenExpiryShallowCheck(ShallowCheck):
    """Template shallow check for OAuth-token expiry on an attached-resource list.

    Subclasses supply three things:

    * ``id`` / ``category`` / ``severity`` — the standard ``BaseCheck`` triple.
    * ``resource_type_ref`` / ``resource_display`` — used to build the
      ``ResourceRef`` and human-readable messages.
    * ``_resources(ctx)`` — the concrete resource list to walk
      (``ctx.mcp_servers`` or ``ctx.tools`` today).

    The base class handles the rest: applicability, connection loading,
    expiry evaluation, and result construction.
    """

    # ``ResourceRef.type`` string emitted on failure — "mcp_server" | "tool".
    resource_type_ref: ClassVar[str]
    # Human-readable singular label used in messages — "MCP server" | "tool".
    resource_display: ClassVar[str]

    # ── template method hooks ─────────────────────────────────────────────

    @abstractmethod
    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        """Return the attached resources of this type from the context."""

    def _resource_name(self, resource: Any) -> str:
        """Override when the resource's user-facing label lives on a
        different attribute than ``.name``."""
        return resource.name

    # ── skip semantics ────────────────────────────────────────────────────

    def applies(self, ctx: CheckContext) -> bool:
        # Only run when at least one attached resource carries an effective
        # OAuth connection id — otherwise the report shows a noisy SKIPPED
        # row for every no-OAuth agent.
        return any(effective_of(r) for r in self._resources(ctx))

    def skip_reason(self, ctx: CheckContext) -> str:
        return f"No OAuth-linked {self.resource_display}s attached."

    # ── main body ─────────────────────────────────────────────────────────

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.oauth_service import OAuthService

        oauth_svc = OAuthService(ctx.db, org_id=ctx.org_id)
        resources = list(self._resources(ctx))
        # Deduplicated set of effective OAuth ids across all resources — a
        # single ``WHERE id IN (...)`` query is a single round-trip regardless
        # of how many resources point at the same connection.
        oauth_ids: List[UUID] = list({
            effective_of(r) for r in resources if effective_of(r) is not None
        })
        connections_by_id = self._load_connections(oauth_svc, oauth_ids)

        expired: List[Tuple[str, str, str]] = []  # (resource_name, connection_label, reason)
        first_failed_id: Optional[str] = None
        checked = 0

        for resource in resources:
            oauth_id = effective_of(resource)
            if oauth_id is None:
                continue
            connection = connections_by_id.get(oauth_id)
            if connection is None:
                # Missing / cross-org / malformed ids are already surfaced by
                # the reachable-deep check and by save-time validation. Not
                # this check's job to double-report them.
                continue
            if not self._uses_time_based_expiry(connection):
                continue
            checked += 1
            reason = self._evaluate_expiry(connection)
            if reason is None:
                continue
            expired.append(
                (self._resource_name(resource), self._connection_label(connection), reason)
            )
            if first_failed_id is None:
                first_failed_id = str(resource.id)

        if checked == 0:
            return self._skip(
                f"No time-based OAuth {self.resource_display} connections attached."
            )
        if expired:
            joined = "; ".join(
                f"'{name}' ({label}): {reason}"
                for name, label, reason in expired[:2]
            )
            more = f"; +{len(expired) - 2} more" if len(expired) > 2 else ""
            return self._fail(
                f"OAuth token expired for {self.resource_display}(s) — {joined}{more}",
                remediation=(
                    f"Reconnect the OAuth account(s) for the affected "
                    f"{self.resource_display}(s)."
                ),
                resource_ref=ResourceRef(
                    type=self.resource_type_ref, id=first_failed_id
                ) if first_failed_id else None,
            )
        return self._pass(
            f"All {checked} OAuth-linked {self.resource_display}(s) have valid tokens."
        )

    # ── helpers (small, focused, unit-testable) ──────────────────────────

    @staticmethod
    def _load_connections(
        oauth_svc, connection_ids: List[UUID]
    ) -> Dict[UUID, OAuthConnection]:
        """Return a ``{id: OAuthConnection}`` map for the requested ids.

        Missing / cross-org ids simply don't appear in the map — treated as
        "not found" by the caller. One round-trip regardless of ``len(ids)``.
        Reuses ``BaseService.query`` (via ``oauth_svc``) so any org-scoping
        filter the service layer applies is honoured, matching the semantics
        of ``get_connection``.
        """
        if not connection_ids:
            return {}
        rows = (
            oauth_svc.query(OAuthConnection)
            .filter(OAuthConnection.id.in_(connection_ids))
            .all()
        )
        return {row.id: row for row in rows}

    @staticmethod
    def _uses_time_based_expiry(connection: OAuthConnection) -> bool:
        """True only for connections whose ``access_token`` has a real
        ``token_expiry`` timestamp we can check without a network call.

        Skipped:
        * ``api_key`` — no token, no expiry.
        * static ``bearer`` — user-supplied fixed token, no expiry stored.
        * ``client_credentials`` — token is minted on demand by the runtime
          resolver, no persisted expiry to compare against.
        """
        metadata = connection.public_metadata or {}
        if metadata.get("auth_kind") in ("bearer", "api_key"):
            return False
        if metadata.get("grant_type") == "client_credentials":
            return False
        if (connection.auth_type or "").lower() == "api_key":
            return False
        return "token_expiry" in metadata

    @staticmethod
    def _evaluate_expiry(connection: OAuthConnection) -> Optional[str]:
        """Return ``None`` when the token is comfortably valid, or a short
        reason string when it's expired or within the 60s buffer."""
        expiry = (connection.public_metadata or {}).get("token_expiry")
        try:
            expiry_i = int(expiry)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        now = int(time.time())
        if now >= expiry_i:
            return f"expired {_humanize_seconds(now - expiry_i)} ago"
        remaining = expiry_i - now
        if remaining <= _EXPIRY_BUFFER_SECONDS:
            return f"expires in {remaining}s"
        return None

    @staticmethod
    def _connection_label(connection: OAuthConnection) -> str:
        return (
            connection.label
            or connection.provider_slug
            or "OAuth connection"
        )


def _humanize_seconds(seconds: int) -> str:
    """Compact duration string for user-facing messages ("42s", "5m", "2h", "3d").

    Kept out of the class so it's trivially unit-testable in isolation."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    return f"{hours // 24}d"
