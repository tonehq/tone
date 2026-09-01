"""``PerResourceCheck`` — the single base for "one row per attached resource".

Many readiness checks inspect a LIST of attached resources (MCP servers, tools,
phone channels/numbers, knowledge bases, OAuth-linked resources) and must emit
**one drawer row per broken resource**, plus a single summary "all good" row.
That skeleton — loop, per-resource ``check_id``, ``resource_ref``, the
pass/summary bookkeeping, and concurrency — used to be copy-pasted into every
such check. This base owns it ONCE.

A subclass declares only *which* resources and *how* to judge one:

    class McpServersConfiguredCheck(PerResourceCheck):
        id = "mcp_servers.configured"
        category = Category.MCP_SERVERS
        severity = Severity.WARNING
        resource_ref_type = "mcp_server"

        def _resources(self, ctx): return ctx.mcp_servers
        def _summary_message(self, n): return f"{n} MCP server(s) configured."
        async def _check_one(self, ctx, server, shared):
            reason = _is_statically_broken(server)
            return None if reason is None else ResourceProblem(f"“{server.name}” … {reason}.", remediation=...)

Extending is "add a subclass + implement ``_check_one``", never "copy the loop"
(OCP). Resources are judged **concurrently** (``asyncio.gather``) — a no-op for
shallow DB checks, a real speed-up for deep network probes. Deep checks set
``probe_timeout`` to bound the whole pass; a timeout is reported as a WARNING
("couldn't verify"), never a publish-blocking failure.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any, AsyncIterator, ClassVar, Iterable, List, Optional

from core.services.readiness.base import BaseCheck, CheckContext
from core.services.readiness.schemas import CheckResult, ResourceRef, Severity


@dataclass
class ResourceProblem:
    """One resource's failure, returned by :meth:`PerResourceCheck._check_one`.

    ``message`` / ``remediation`` are the user-facing copy. ``severity``
    overrides the check's class severity for this one resource (e.g. phone
    verification is a BLOCKER on a pure-inbound agent, a WARNING otherwise).
    ``oauth_connection_id`` populates the ``ResourceRef`` side-channel the
    drawer uses for a targeted "reconnect" affordance.
    """

    message: str
    remediation: Optional[str] = None
    severity: Optional[Severity] = None
    oauth_connection_id: Optional[str] = None


class PerResourceCheck(BaseCheck):
    """Base for checks that emit one result per attached resource."""

    # ``ResourceRef.type`` to stamp on each failure row (e.g. "mcp_server",
    # "tool", "channel", "phone_number", "knowledge_base"). Leave as ``None``
    # for checks whose "resource" isn't a navigable entity (e.g. grouped by
    # provider) — those rows carry no ResourceRef.
    resource_ref_type: ClassVar[Optional[str]] = None
    # Overall budget for the whole pass, in seconds. ``None`` = no timeout
    # (shallow checks). Set on deep checks; a timeout → one WARNING row.
    probe_timeout: ClassVar[Optional[float]] = None

    # ── subclass hooks ───────────────────────────────────────────────────────

    def _resources(self, ctx: CheckContext) -> Iterable[Any]:
        """The resources to judge. Usually a ``ctx`` attachment list."""
        raise NotImplementedError

    def _resource_id(self, resource: Any) -> str:
        """Stable id for the per-resource ``check_id`` + ``ResourceRef``.
        Defaults to ``resource.id``; override when the id lives elsewhere."""
        return str(resource.id)

    def _summary_message(self, count: int) -> str:
        """The single PASS row shown when every resource is fine."""
        raise NotImplementedError

    async def _check_one(
        self, ctx: CheckContext, resource: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        """Judge ONE resource. Return a :class:`ResourceProblem` on failure, or
        ``None`` when it's fine. ``shared`` is whatever :meth:`_shared` yielded
        (e.g. an ``httpx.AsyncClient`` reused across resources), or ``None``."""
        raise NotImplementedError

    @contextlib.asynccontextmanager
    async def _shared(self, ctx: CheckContext) -> AsyncIterator[Any]:
        """Optional shared resource (pooled HTTP client, service handles) built
        once and passed to every :meth:`_check_one`. Default: nothing."""
        yield None

    # ── the one implementation ───────────────────────────────────────────────

    async def run(self, ctx: CheckContext) -> List[CheckResult]:
        resources = list(self._resources(ctx))
        if not resources:
            # ``applies`` normally guards this; stay safe when called directly.
            return [self._pass(self._summary_message(0))]

        try:
            outcomes = await self._evaluate_all(ctx, resources)
        except asyncio.TimeoutError:
            # Whole pass exceeded ``probe_timeout``: couldn't confirm in time.
            # That's a WARNING ("slow"), never a publish-blocking failure —
            # mirrors the deep-probe timeout doctrine.
            return [self._fail(
                self._timeout_message(len(resources)),
                remediation="This is usually a temporary slowdown. Re-run the check in a moment.",
                severity=Severity.WARNING,
            )]

        results = [
            self._fail(
                problem.message,
                remediation=problem.remediation,
                resource_ref=self._resource_ref(resource, problem),
                check_id=self._result_id(self._resource_id(resource)),
                severity=problem.severity,
            )
            for resource, problem in zip(resources, outcomes)
            if problem is not None
        ]
        if results:
            return results
        return [self._pass(self._summary_message(len(resources)))]

    # ── internals ────────────────────────────────────────────────────────────

    async def _evaluate_all(
        self, ctx: CheckContext, resources: List[Any]
    ) -> List[Optional[ResourceProblem]]:
        async with self._shared(ctx) as shared:
            coro = asyncio.gather(
                *(self._check_one(ctx, r, shared) for r in resources)
            )
            if self.probe_timeout is None:
                return await coro
            return await asyncio.wait_for(coro, timeout=self.probe_timeout)

    def _resource_ref(
        self, resource: Any, problem: ResourceProblem
    ) -> Optional[ResourceRef]:
        if self.resource_ref_type is None:
            return None
        return ResourceRef(
            type=self.resource_ref_type,
            id=self._resource_id(resource),
            oauth_connection_id=problem.oauth_connection_id,
        )

    def _timeout_message(self, count: int) -> str:
        """Copy for the whole-pass timeout WARNING. Override for a warmer line."""
        return "Couldn't verify these in time — they may be slow. Run the check again."
