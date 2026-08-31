"""Runner — the "conveyor belt" that sends the context past every applicable check.

Has zero business logic. The only interesting decisions are:
  1. Skip vs run (delegates to ``check.applies(ctx)``).
  2. Aggregate ``CheckResult[]`` into ``ReadinessReport`` (severity math).
  3. Concurrency: Deep checks are async and hit external providers, so we
     ``asyncio.gather`` them; Shallow checks are cheap and also run under gather
     for symmetry (no measurable overhead).

If the runner ever grows a knob (e.g. per-org check exclusions) it should be a
new module — this file stays a pure orchestrator.
"""

from __future__ import annotations

from typing import List, Optional, Set
from uuid import UUID

import anyio
from loguru import logger

from core.services.readiness.base import BaseCheck, CheckContext
from core.services.readiness.registry import get_checks
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    Depth,
    OverallStatus,
    ReadinessReport,
    Severity,
    Status,
)


class Runner:
    """Executes a set of checks against a pre-built context and aggregates."""

    async def run(
        self,
        ctx: CheckContext,
        *,
        deep_categories: Optional[Set[Category]] = None,
    ) -> ReadinessReport:
        """Run readiness against ``ctx``.

        ``deep_categories`` is meaningful only when ``ctx.depth == DEEP``:

        * ``None`` (default) — every deep check runs (the existing full-deep
          behavior; used by publish gate and the manual "Test" button).
        * ``set(...)`` — only deep checks whose ``category`` is in the set run;
          other deep checks return ``SKIPPED`` with a clear reason. Shallow
          checks always run either way. Used by the save flow to probe only
          the resources the user actually touched.
        """
        checks = get_checks(ctx.depth)
        results = await self._execute_all(checks, ctx, deep_categories=deep_categories)
        return self._aggregate(
            results,
            depth=ctx.depth,
            agent_id=ctx.agent.id if ctx.agent else None,
            config_id=ctx.config.id if ctx.config else None,
        )

    # ── execution ──────────────────────────────────────────────────────────

    async def _execute_all(
        self,
        checks: List[BaseCheck],
        ctx: CheckContext,
        *,
        deep_categories: Optional[Set[Category]] = None,
    ) -> List[CheckResult]:
        """Run every check concurrently. A single check crashing does not abort
        the report — its slot returns a FAIL result explaining the crash so ops
        can find it in the response instead of a swallowed 500."""

        async def run_one(check: BaseCheck) -> List[CheckResult]:
            # A check may return a single CheckResult or a list of per-resource
            # results (e.g. one row per MCP server). Everything below is
            # normalised to a list so the aggregator sees a flat stream.
            #
            # Targeted-deep filter: shallow checks always run; deep checks
            # outside the requested category set short-circuit to SKIPPED so
            # the report shape stays identical to a full-deep run. The single
            # marker row is enough for the frontend merge to detect that the
            # whole category was left unprobed on this save.
            if (
                deep_categories is not None
                and check.depth == Depth.DEEP
                and check.category not in deep_categories
            ):
                return [check._skip(
                    f"Not re-probed on this save ({check.category.value} unchanged)."
                )]
            if not check.applies(ctx):
                return [check._skip(check.skip_reason(ctx))]
            try:
                outcome = await check.run(ctx)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "[readiness] check {} crashed for agent {}",
                    check.id,
                    getattr(ctx.agent, "id", None),
                )
                return [check._fail(
                    f"Internal error running check: {exc}",
                    remediation=(
                        "Please retry. If it persists, contact support with "
                        f"check id '{check.id}'."
                    ),
                )]
            return outcome if isinstance(outcome, list) else [outcome]

        results: List[Optional[List[CheckResult]]] = [None] * len(checks)

        async def _wrapper(index: int, chk: BaseCheck) -> None:
            results[index] = await run_one(chk)

        async with anyio.create_task_group() as tg:
            for i, c in enumerate(checks):
                tg.start_soon(_wrapper, i, c)

        return [r for sub in results if sub for r in sub]

    # ── aggregation ────────────────────────────────────────────────────────

    def _aggregate(
        self,
        results: List[CheckResult],
        *,
        depth: Depth,
        agent_id: Optional[UUID],
        config_id: Optional[UUID],
    ) -> ReadinessReport:
        blockers = _count(results, Status.FAIL, Severity.BLOCKER)
        warnings = _count(results, Status.FAIL, Severity.WARNING)
        info = _count(results, Status.FAIL, Severity.INFO)
        passed = sum(1 for r in results if r.status == Status.PASS)
        skipped = sum(1 for r in results if r.status == Status.SKIPPED)

        if blockers:
            overall = OverallStatus.NOT_READY
        elif warnings:
            overall = OverallStatus.READY_WITH_WARNINGS
        else:
            overall = OverallStatus.READY

        return ReadinessReport(
            agent_id=str(agent_id) if agent_id else "",
            config_id=str(config_id) if config_id else None,
            depth=depth,
            overall_status=overall,
            summary={
                "blockers": blockers,
                "warnings": warnings,
                "info": info,
                "passed": passed,
                "skipped": skipped,
            },
            checks=results,
        )


def _count(results: List[CheckResult], status: Status, severity: Severity) -> int:
    return sum(1 for r in results if r.status == status and r.severity == severity)
