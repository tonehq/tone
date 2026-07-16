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

from typing import List, Optional
from uuid import UUID

import anyio
from loguru import logger

from core.services.readiness.base import BaseCheck, CheckContext
from core.services.readiness.registry import get_checks
from core.services.readiness.schemas import (
    CheckResult,
    Depth,
    OverallStatus,
    ReadinessReport,
    Severity,
    Status,
)


class Runner:
    """Executes a set of checks against a pre-built context and aggregates."""

    async def run(self, ctx: CheckContext) -> ReadinessReport:
        checks = get_checks(ctx.depth)
        results = await self._execute_all(checks, ctx)
        return self._aggregate(
            results,
            depth=ctx.depth,
            agent_id=ctx.agent.id if ctx.agent else None,
            config_id=ctx.config.id if ctx.config else None,
        )

    # ── execution ──────────────────────────────────────────────────────────

    async def _execute_all(
        self, checks: List[BaseCheck], ctx: CheckContext
    ) -> List[CheckResult]:
        """Run every check concurrently. A single check crashing does not abort
        the report — its slot returns a FAIL result explaining the crash so ops
        can find it in the response instead of a swallowed 500."""

        async def run_one(check: BaseCheck) -> CheckResult:
            if not check.applies(ctx):
                return check._skip(check.skip_reason(ctx))
            try:
                return await check.run(ctx)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "[readiness] check {} crashed for agent {}",
                    check.id,
                    getattr(ctx.agent, "id", None),
                )
                return check._fail(
                    f"Internal error running check: {exc}",
                    remediation=(
                        "Please retry. If it persists, contact support with "
                        f"check id '{check.id}'."
                    ),
                )

        results: List[Optional[CheckResult]] = [None] * len(checks)

        async def _wrapper(index: int, chk: BaseCheck) -> None:
            results[index] = await run_one(chk)

        async with anyio.create_task_group() as tg:
            for i, c in enumerate(checks):
                tg.start_soon(_wrapper, i, c)

        return [r for r in results if r is not None]

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
