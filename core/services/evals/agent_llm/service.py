"""``AgentLlmEvalService`` — orchestrator for the per-agent LLM eval harness.

Transport-agnostic: takes a SQLAlchemy session + plain args, returns a
dataclass ``AgentLlmRunSummary``. The CLI (``evals/agent_llm_eval.py``) is a
thin adapter; a FastAPI adapter can be added later without touching this
class.

Shape mirrors ``EvalService``:
- ``run_eval`` snapshots the agent's config, closes the caller's DB session,
  runs the LLM/judge loop with NO open session, then bulk-inserts on a fresh
  short-lived session at the tail (Neon ``idle_in_transaction_session_timeout``
  would otherwise drop a session held across the LLM loop).
- Fail-soft per scenario — one scenario failing (LLM error / judge error)
  stamps that row ``status='failed'`` with the exception on ``answer_error``
  or ``judge_error``; the batch continues.
- Fail-loud on configuration — ``EvalConfigurationError`` /
  ``AgentLlmEvalConfigError`` re-raise so the run aborts cleanly before any
  fake-FAIL rows are written.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models.agent_llm_eval_result import AgentLlmEvalResult
from core.services.evals.agent_llm.agent_config_loader import (
    AgentConfigLoader,
    AgentEvalConfig,
)
from core.services.evals.errors import (
    AgentLlmEvalConfigError,
    EvalConfigurationError,
)
from core.services.llm.chat_complete import chat_complete
from shared.config import settings


_JUDGE_ENGINE = "deepeval"

# Every ``triggered_by`` value the audit surface will accept — enforced both
# at ``run_eval`` and inside the Procrastinate task. ``'manual'`` covers the
# user-clicked "Run Eval" button in the FE (matches the RAG task's use of
# ``'manual'`` for the same UX pattern); ``'api'`` covers programmatic
# integrations; ``'cli'`` is the historical fixture-driven CLI.
TRIGGERED_BY_VALUES: frozenset[str] = frozenset({"cli", "api", "manual"})


@dataclass
class AgentLlmRunSummary:
    """Snapshot of one agent-LLM eval run. Identity is ``run_id`` (UUID
    stamped across every row of the batch); ``run_number`` is the per-agent
    monotonic sequence for human ordering."""

    run_id: UUID
    agent_id: UUID
    run_number: int
    triggered_by: str
    judge_model: Optional[str]
    # Answer model — the LLM the agent used to answer each scenario. All
    # rows in one run share the same value (config is snapshotted once at
    # run start), so it's safe to include in the grouped summary via a
    # single-value GROUP BY.
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    status: str  # 'completed' | 'failed'
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary: dict = field(default_factory=dict)


class AgentLlmEvalService:
    def __init__(
        self,
        *,
        judge: object | None = None,
        agent_loader: AgentConfigLoader | None = None,
    ) -> None:
        # Both DI seams are optional — production callers construct with no
        # args (the judge is built lazily so read-only paths never import
        # DeepEval); tests inject stubs to avoid the SDK.
        self._injected_judge = judge
        self._loader = agent_loader or AgentConfigLoader()

    @property
    def _judge(self):
        """Lazily build the judge on first use so `list_runs` / `get_run_detail`
        (read-only paths) never transitively import DeepEval."""
        if self._injected_judge is None:
            # Local import keeps DeepEval + its OTel hijack out of any process
            # that only reads the results table.
            from core.services.evals.agent_llm.agent_llm_judge import (
                AgentLlmJudgeService,
            )

            self._injected_judge = AgentLlmJudgeService()
        return self._injected_judge

    # ── Public API ──────────────────────────────────────────────────────

    def run_eval(
        self,
        db: Session,
        *,
        agent_id: UUID,
        scenarios: List[Any],  # list[LLMScenario] — kept loose to avoid a hard import
        triggered_by: str = "cli",
        judge_model: Optional[str] = None,
        run_id: Optional[UUID] = None,
    ) -> AgentLlmRunSummary:
        """Execute every ``LLMScenario`` against the agent's LLM. Persists
        one ``agent_llm_eval_results`` row per scenario tagged with the same
        ``run_id`` + per-agent ``run_number``.

        Never re-raises on scenario failures — the run always terminates with
        an ``AgentLlmRunSummary``. Configuration errors (missing published
        config, bad metric name, …) DO re-raise so the CLI exits with an
        actionable message instead of writing garbage rows.
        """
        if triggered_by not in TRIGGERED_BY_VALUES:
            raise ValueError(
                f"triggered_by must be one of {sorted(TRIGGERED_BY_VALUES)}; "
                f"got {triggered_by!r}"
            )
        if not scenarios:
            raise AgentLlmEvalConfigError(
                f"No scenarios to run for agent {agent_id} — check --tag / "
                "agent_slug filters"
            )

        # Pre-flight: every scenario must resolve to a non-empty metric list.
        # Without this, a scenario with ``metrics=[]`` combined with an unset
        # env would raise ``EvalConfigurationError`` MID-loop, after earlier
        # scenarios had already burned real LLM calls — those scored rows
        # would be discarded because the persist step runs only after the
        # loop. Fail loudly here BEFORE spending any tokens.
        default_metrics = list(settings.AGENT_LLM_EVAL_METRICS_ENABLED or [])
        for s in scenarios:
            resolved = list(s.metrics or default_metrics)
            if not resolved:
                raise AgentLlmEvalConfigError(
                    f"Scenario {s.name!r} has no metrics enabled — set "
                    "AGENT_LLM_EVAL_METRICS_ENABLED or LLMScenario.metrics."
                )

        run_id = run_id or uuid.uuid4()

        # 1. Snapshot the agent's config while the session is still open,
        # then close it so nothing is held during the LLM loop.
        agent_config: AgentEvalConfig = self._loader.load_for_eval(db, agent_id)

        # Resolve judge model with per-org override (DB → env → hardcoded
        # default). Uses the AGENT-LLM resolver (``llm_evals.judge_model``,
        # AGENT_LLM_EVAL_JUDGE_MODEL env, hardcoded fallback) so this CLI /
        # fixture path stays in lock-step with ``run_eval_for_agent`` — one
        # judge policy for agent-LLM evals regardless of transport. Explicit
        # caller kwarg still wins so the CLI can pin a specific model.
        if judge_model is None:
            from core.services.org_settings import (
                load_agent_llm_eval_settings_for_org,
            )

            judge_model = load_agent_llm_eval_settings_for_org(
                db, agent_config.organization_id
            ).judge_model
        next_run_number = self._next_run_number(
            db,
            agent_id=agent_config.agent_id,
            organization_id=agent_config.organization_id,
        )
        db.close()

        started_at = datetime.now(timezone.utc)
        run_summary = AgentLlmRunSummary(
            run_id=run_id,
            agent_id=agent_config.agent_id,
            run_number=next_run_number,
            triggered_by=triggered_by,
            judge_model=judge_model,
            status="running",
            error=None,
            started_at=started_at,
            completed_at=None,
            summary={},
        )

        logger.info(
            "[agent-llm-eval] running run_id={} agent={} run_number={} "
            "scenarios={} judge_model={} triggered_by={}",
            run_id, agent_config.agent_name, next_run_number,
            len(scenarios), judge_model, triggered_by,
        )

        # 2. Score every scenario (fail-soft per row).
        scored_rows: List[dict] = []
        try:
            # Judge key defaults to the agent's own provider key when the
            # judge model implicitly uses the same provider. But the judge
            # model is separately configurable, so we resolve its key on a
            # short-lived session per-run instead of holding one open.
            judge_key = self._resolve_judge_key(
                organization_id=agent_config.organization_id,
                judge_model=judge_model,
                fallback_provider=agent_config.llm_provider,
                fallback_key=agent_config.llm_api_key,
            )

            for scenario in scenarios:
                scored_rows.append(
                    self._score_one_scenario(
                        scenario=scenario,
                        agent_config=agent_config,
                        judge_model=judge_model,
                        judge_key=judge_key,
                    )
                )

            completed_at = datetime.now(timezone.utc)
            self._persist_result_batch(
                organization_id=agent_config.organization_id,
                agent_config=agent_config,
                run_id=run_id,
                run_number=next_run_number,
                triggered_by=triggered_by,
                judge_model=judge_model,
                started_at=started_at,
                completed_at=completed_at,
                scored_rows=scored_rows,
            )
            run_summary.status = "completed"
            run_summary.completed_at = completed_at
            run_summary.summary = _summarize_scored_rows(scored_rows)
            logger.info(
                "[agent-llm-eval] completed run_id={} run_number={} pass={} "
                "fail={} pass_rate={:.2%}",
                run_id, next_run_number,
                run_summary.summary.get("pass", 0),
                run_summary.summary.get("fail", 0),
                run_summary.summary.get("pass_rate", 0.0),
            )
        except (EvalConfigurationError, AgentLlmEvalConfigError):
            # Systemic config error — the whole batch is bad, don't
            # persist. Re-raise so the caller (CLI) surfaces the message
            # and exits non-zero.
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[agent-llm-eval] run failed run_id={} run_number={}",
                run_id, next_run_number,
            )
            self._mark_failed(
                run_summary=run_summary,
                agent_config=agent_config,
                scenarios=scenarios,
                scored_rows=scored_rows,
                judge_model=judge_model,
                error=f"{type(e).__name__}: {e}",
            )

        return run_summary

    def run_eval_for_agent(
        self,
        db: Session,
        *,
        agent_id: UUID,
        triggered_by: str = "manual",
        judge_model: Optional[str] = None,
        scenario_ids: Optional[List[UUID]] = None,
        tags: Optional[List[str]] = None,
        run_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
    ) -> AgentLlmRunSummary:
        """DB-backed entry point — loads scenarios from
        ``agent_llm_eval_scenarios`` and delegates to :meth:`run_eval`.

        This is what the API routes, the Procrastinate task, and future
        cron jobs call; the CLI fixture path stays on the in-memory
        :meth:`run_eval` so tests / one-off fixture runs work unchanged.
        Existing behavior is 100% preserved — the delegate signature is not
        touched.

        Scenario filter precedence: ``scenario_ids`` narrows first (exact
        set); ``tags`` narrows via JSONB has-any-of match; no filters =
        every scenario for the agent.
        """
        from core.services.evals.agent_llm.scenario_service import (
            AgentLlmScenarioService,
            scenario_row_to_llm_scenario,
        )
        from core.services.org_settings import (
            load_agent_llm_eval_settings_for_org,
        )

        # Resolve the agent's organization_id BEFORE calling into the
        # scenario service — the caller may not know it yet (Procrastinate
        # task only receives ``agent_id``).
        if organization_id is None:
            from core.models.agent import Agent

            org_row = (
                db.query(Agent.organization_id)
                .filter(Agent.id == agent_id)
                .first()
            )
            if org_row is None:
                raise AgentLlmEvalConfigError(
                    f"Agent {agent_id} not found — cannot resolve org for eval"
                )
            organization_id = org_row[0]

        scenarios_service = AgentLlmScenarioService(db, org_id=organization_id)
        rows = scenarios_service.load_all_for_run(
            agent_id,
            scenario_ids=scenario_ids,
            tags=tags,
        )
        if not rows:
            raise AgentLlmEvalConfigError(
                f"No scenarios found for agent {agent_id} — create scenarios "
                "under the LLM Evals tab before running an eval."
            )
        llm_scenarios = [scenario_row_to_llm_scenario(r) for r in rows]

        # Resolve judge_model with the AGENT-LLM resolver (falls back through
        # ``agent_llm.judge_model`` → env → hardcoded default). Explicit
        # caller kwarg still wins so the FE Run modal's per-run override
        # threads through unchanged.
        if judge_model is None:
            judge_model = load_agent_llm_eval_settings_for_org(
                db, organization_id
            ).judge_model

        return self.run_eval(
            db,
            agent_id=agent_id,
            scenarios=llm_scenarios,
            triggered_by=triggered_by,
            judge_model=judge_model,
            run_id=run_id,
        )

    def compare_runs(
        self,
        db: Session,
        *,
        org_id: UUID,
        baseline_run_id: UUID,
        candidate_run_id: UUID,
        score_drop: float = 0.15,
    ) -> dict:
        """Diff two agent-LLM eval runs. Same output shape as
        :meth:`EvalService.compare_results` (baseline / candidate summary,
        per-scenario diff, regression list) so the FE compare view uses
        one component across both eval flavors.

        Org-scoped: both runs must belong to ``org_id`` — a cross-tenant
        run id raises ``EvalConfigurationError`` rather than silently
        producing a nonsensical diff.
        """
        baseline = self.get_run_detail(db, org_id=org_id, run_id=baseline_run_id)
        candidate = self.get_run_detail(db, org_id=org_id, run_id=candidate_run_id)
        if baseline is None or candidate is None:
            raise EvalConfigurationError(
                f"compare_runs: missing run (baseline={baseline_run_id}, "
                f"candidate={candidate_run_id})"
            )
        return _diff_agent_llm_runs(
            baseline_summary=baseline["summary"],
            candidate_summary=candidate["summary"],
            baseline_rows=baseline["scenarios"],
            candidate_rows=candidate["scenarios"],
            score_drop=score_drop,
        )

    def list_runs(
        self,
        db: Session,
        *,
        agent_id: UUID,
        organization_id: Optional[UUID] = None,
        limit: Optional[int] = None,
    ) -> List[AgentLlmRunSummary]:
        """Return each run's aggregate summary for one agent, newest first.

        ``organization_id`` is optional today (CLI is single-tenant); a
        future API adapter MUST pass ``org_id`` from ``JWTClaims`` — without
        it a caller that guesses another tenant's ``agent_id`` can read
        every historical run summary for that agent.
        """
        rows = _run_grouped_query(
            db, agent_id=agent_id, organization_id=organization_id
        ).all()
        summaries = [_row_to_run_summary(r) for r in rows]
        if limit is not None:
            summaries = summaries[:limit]
        return summaries

    def get_run_detail(
        self,
        db: Session,
        *,
        org_id: UUID,
        run_id: UUID,
    ) -> Optional[dict]:
        """Return ``{"summary", "scenarios"}`` for one run, org-scoped so a
        caller from another tenant sees ``None`` even with a valid ``run_id``.
        """
        summary_row = _run_grouped_query(
            db, run_id=run_id, organization_id=org_id
        ).first()
        if summary_row is None:
            return None
        summary = _row_to_run_summary(summary_row)
        scenario_rows = (
            db.query(AgentLlmEvalResult)
            .filter(
                AgentLlmEvalResult.run_id == run_id,
                AgentLlmEvalResult.organization_id == org_id,
            )
            .order_by(AgentLlmEvalResult.scenario_key.asc())
            .all()
        )
        return {
            "summary": summary,
            "scenarios": [row.to_dict() for row in scenario_rows],
        }

    # ── Internals ───────────────────────────────────────────────────────

    def _next_run_number(
        self,
        db: Session,
        *,
        agent_id: UUID,
        organization_id: UUID,
    ) -> int:
        """Compute the next per-(agent, org) monotonic run number.

        Tenant-scoped so a future API adapter can't have another org's runs
        contribute to this agent's sequence (agents are unique per org so
        the org filter is theoretically redundant today, but adding it
        keeps the invariant explicit and mirrors the eventual ``list_runs``
        filter).
        """
        row = (
            db.query(func.coalesce(func.max(AgentLlmEvalResult.run_number), 0) + 1)
            .filter(
                AgentLlmEvalResult.agent_id == agent_id,
                AgentLlmEvalResult.organization_id == organization_id,
            )
            .scalar()
        )
        return int(row or 1)

    def _resolve_judge_key(
        self,
        *,
        organization_id: UUID,
        judge_model: str,
        fallback_provider: Optional[str],
        fallback_key: Optional[str],
    ) -> str:
        """The judge model may point at a different provider than the agent
        (e.g. agent on Anthropic, judge on OpenAI). Resolve the key via the
        shared router; fall back to the agent's own key when the two share
        a provider so dev machines with only ONE key set still work."""
        from core.database.session import SessionLocal
        from core.services.llm.chat_complete import resolve_provider
        from core.services.rag.provider_keys import ProviderKeyService

        try:
            judge_provider = resolve_provider(judge_model)
        except Exception as e:  # noqa: BLE001
            raise AgentLlmEvalConfigError(
                f"Cannot resolve provider for judge model {judge_model!r}: {e}"
            ) from e

        if fallback_provider and judge_provider == fallback_provider and fallback_key:
            return fallback_key

        with SessionLocal() as tmp:
            key = ProviderKeyService.get_key(tmp, organization_id, judge_provider)
        if not key:
            raise AgentLlmEvalConfigError(
                f"No {judge_provider!r} API key configured for organisation "
                f"{organization_id} (needed by judge model {judge_model!r})."
            )
        return key

    def _score_one_scenario(
        self,
        *,
        scenario: Any,
        agent_config: AgentEvalConfig,
        judge_model: str,
        judge_key: str,
    ) -> dict:
        """Run one scenario through the agent's LLM + the DeepEval judge.
        Fail-soft: an LLM or judge exception is captured on the scored dict
        so peer scenarios still score."""
        t0 = time.monotonic()
        actual_answer = ""
        answer_error: Optional[str] = None
        judge_error: Optional[str] = None
        judge_out: dict = {}

        messages = _build_messages(agent_config.system_prompt, scenario.prompt)

        try:
            actual_answer = chat_complete(
                model=agent_config.llm_model,
                api_key=agent_config.llm_api_key,
                messages=messages,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens,
                json_mode=False,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[agent-llm-eval] agent LLM failed scenario={} model={}",
                scenario.name, agent_config.llm_model,
            )
            answer_error = f"{type(e).__name__}: {e}"

        # Judge only when we have an actual answer — a failed LLM call yields
        # an empty string and every metric would trivially FAIL, obscuring
        # the real cause (the LLM error).
        if answer_error is None:
            enabled_metrics = list(
                scenario.metrics or settings.AGENT_LLM_EVAL_METRICS_ENABLED
            )
            threshold = (
                scenario.threshold
                if scenario.threshold is not None
                else settings.EVAL_METRIC_THRESHOLD
            )
            try:
                judge_out = self._judge.judge(
                    prompt=scenario.prompt,
                    system_prompt=agent_config.system_prompt,
                    actual_output=actual_answer,
                    api_key=judge_key,
                    model=judge_model,
                    metrics=enabled_metrics,
                    threshold=threshold,
                    expected_output=scenario.expected_answer,
                    persona_criteria=scenario.persona_criteria,
                    instruction_criteria=scenario.instruction_criteria,
                )
            except EvalConfigurationError:
                # Bad config — abort the whole run, don't just this scenario.
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    "[agent-llm-eval] judge failed scenario={}", scenario.name,
                )
                judge_error = f"{type(e).__name__}: {e}"

        latency_ms = int((time.monotonic() - t0) * 1000)

        status = "failed" if (answer_error or judge_error) else "completed"
        return {
            "scenario": scenario,
            "actual_answer": actual_answer,
            "judge": judge_out,
            "latency_ms": latency_ms,
            "answer_error": answer_error,
            "judge_error": judge_error,
            "status": status,
        }

    def _persist_result_batch(
        self,
        *,
        organization_id: UUID,
        agent_config: AgentEvalConfig,
        run_id: UUID,
        run_number: int,
        triggered_by: str,
        judge_model: str,
        started_at: datetime,
        completed_at: datetime,
        scored_rows: List[dict],
    ) -> None:
        """Bulk-insert every scored scenario on a brand-new session so we
        never inherit a broken pool connection from the LLM-loop session."""
        if not scored_rows:
            return
        rows: List[dict] = []
        for scored in scored_rows:
            scenario = scored["scenario"]
            judge = scored.get("judge") or {}
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "agent_id": agent_config.agent_id,
                    "agent_config_id": agent_config.agent_config_id,
                    "run_id": run_id,
                    "run_number": run_number,
                    "triggered_by": triggered_by,
                    "scenario_key": scenario.name,
                    "scenario_tags": list(scenario.tags) if scenario.tags else None,
                    "prompt": scenario.prompt,
                    "expected_answer": scenario.expected_answer,
                    "llm_model": agent_config.llm_model,
                    "llm_provider": agent_config.llm_provider,
                    "system_prompt": agent_config.system_prompt,
                    "llm_settings_snapshot": agent_config.llm_settings_snapshot or None,
                    "judge_model": judge_model,
                    "judge_engine": _JUDGE_ENGINE,
                    "status": scored["status"],
                    "actual_answer": scored.get("actual_answer") or None,
                    "verdict": judge.get("verdict"),
                    "metric_scores": judge.get("metric_scores") or None,
                    "judge_reasoning": judge.get("reasoning") or None,
                    "latency_ms": scored.get("latency_ms"),
                    "answer_error": scored.get("answer_error"),
                    "judge_error": scored.get("judge_error"),
                    "started_at": started_at,
                    "completed_at": completed_at,
                }
            )

        from core.database.session import SessionLocal
        with SessionLocal() as fresh:
            fresh.bulk_insert_mappings(AgentLlmEvalResult, rows)
            fresh.commit()
        logger.info(
            "[agent-llm-eval] persisted run_id={} rows={} completed={} failed={}",
            run_id, len(rows),
            sum(1 for r in rows if r["status"] == "completed"),
            sum(1 for r in rows if r["status"] == "failed"),
        )

    def _mark_failed(
        self,
        *,
        run_summary: AgentLlmRunSummary,
        agent_config: AgentEvalConfig,
        scenarios: List[Any],
        scored_rows: List[dict],
        judge_model: str,
        error: str,
    ) -> None:
        """Persist whatever we DID score before the crash, then stamp
        placeholder failed rows for the rest so the batch has one row per
        scenario for downstream aggregation."""
        logger.warning(
            "[agent-llm-eval] marking run_id={} failed error={}",
            run_summary.run_id, error,
        )
        scored_keys = {r["scenario"].name for r in scored_rows}
        for scenario in scenarios:
            if scenario.name in scored_keys:
                continue
            scored_rows.append(
                {
                    "scenario": scenario,
                    "actual_answer": "",
                    "judge": {},
                    "latency_ms": None,
                    "answer_error": error,
                    "judge_error": None,
                    "status": "failed",
                }
            )
        completed_at = datetime.now(timezone.utc)
        try:
            self._persist_result_batch(
                organization_id=agent_config.organization_id,
                agent_config=agent_config,
                run_id=run_summary.run_id,
                run_number=run_summary.run_number,
                triggered_by=run_summary.triggered_by,
                judge_model=judge_model,
                started_at=run_summary.started_at or completed_at,
                completed_at=completed_at,
                scored_rows=scored_rows,
            )
        except Exception:
            logger.exception(
                "[agent-llm-eval] _mark_failed persist failed run_id={}",
                run_summary.run_id,
            )
        run_summary.status = "failed"
        run_summary.error = error
        run_summary.completed_at = completed_at
        run_summary.summary = _summarize_scored_rows(
            [r for r in scored_rows if r["status"] == "completed"]
        )


def _build_messages(system_prompt: Optional[str], user_prompt: str) -> List[dict]:
    msgs: List[dict] = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.append({"role": "user", "content": user_prompt})
    return msgs


def _summarize_scored_rows(rows: List[dict]) -> dict:
    """Roll up the in-memory scored-row list — mirrors ``EvalService``'s
    summarizer shape (counts + rates + per-metric averages) so callers built
    against the RAG summary work here too."""
    total = len(rows)
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    latency_sum = 0
    metric_sums: dict[str, float] = {}
    metric_counts: dict[str, int] = {}

    for r in rows:
        judge = r.get("judge") or {}
        v = (judge.get("verdict") or "FAIL")
        counts[v] = counts.get(v, 0) + 1
        latency_sum += int(r.get("latency_ms") or 0)
        for name, entry in (judge.get("metric_scores") or {}).items():
            if not isinstance(entry, dict):
                continue
            score = entry.get("score")
            if score is None:
                continue
            metric_sums[name] = metric_sums.get(name, 0.0) + float(score)
            metric_counts[name] = metric_counts.get(name, 0) + 1

    summary = {
        "total": total,
        "pass": counts["PASS"],
        "partial": counts["PARTIAL"],
        "fail": counts["FAIL"],
        "pass_rate": (counts["PASS"] / total) if total else 0.0,
        "partial_rate": (counts["PARTIAL"] / total) if total else 0.0,
        "fail_rate": (counts["FAIL"] / total) if total else 0.0,
        "duration_ms": latency_sum,
    }
    for name, s in metric_sums.items():
        cnt = metric_counts.get(name, 0)
        summary[f"avg_{name}"] = (s / cnt) if cnt else 0.0
    return summary


def _run_grouped_query(
    db: Session,
    *,
    agent_id: Optional[UUID] = None,
    run_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
):
    from sqlalchemy import case as _case

    q = (
        db.query(
            AgentLlmEvalResult.run_id.label("run_id"),
            AgentLlmEvalResult.agent_id.label("agent_id"),
            AgentLlmEvalResult.organization_id.label("organization_id"),
            AgentLlmEvalResult.run_number.label("run_number"),
            AgentLlmEvalResult.triggered_by.label("triggered_by"),
            AgentLlmEvalResult.judge_model.label("judge_model"),
            # Answer model — snapshotted identically on every row of a run,
            # so it groups to a single value per run_id. Surfaces on the FE
            # Run history table so users see which agent model produced the
            # answers being scored.
            AgentLlmEvalResult.llm_model.label("llm_model"),
            AgentLlmEvalResult.llm_provider.label("llm_provider"),
            AgentLlmEvalResult.started_at.label("started_at"),
            AgentLlmEvalResult.completed_at.label("completed_at"),
            func.count(AgentLlmEvalResult.id).label("total"),
            func.sum(_case((AgentLlmEvalResult.verdict == "PASS", 1), else_=0)).label("pass_count"),
            func.sum(_case((AgentLlmEvalResult.verdict == "PARTIAL", 1), else_=0)).label("partial_count"),
            func.sum(_case((AgentLlmEvalResult.verdict == "FAIL", 1), else_=0)).label("fail_count"),
            func.sum(_case((AgentLlmEvalResult.status == "failed", 1), else_=0)).label("failed_status_count"),
            func.coalesce(func.sum(AgentLlmEvalResult.latency_ms), 0).label("duration_ms"),
        )
        .group_by(
            AgentLlmEvalResult.run_id,
            AgentLlmEvalResult.agent_id,
            AgentLlmEvalResult.organization_id,
            AgentLlmEvalResult.run_number,
            AgentLlmEvalResult.triggered_by,
            AgentLlmEvalResult.judge_model,
            AgentLlmEvalResult.llm_model,
            AgentLlmEvalResult.llm_provider,
            AgentLlmEvalResult.started_at,
            AgentLlmEvalResult.completed_at,
        )
        .order_by(AgentLlmEvalResult.started_at.desc())
    )
    if agent_id is not None:
        q = q.filter(AgentLlmEvalResult.agent_id == agent_id)
    if run_id is not None:
        q = q.filter(AgentLlmEvalResult.run_id == run_id)
    if organization_id is not None:
        q = q.filter(AgentLlmEvalResult.organization_id == organization_id)
    return q


def _row_to_run_summary(row) -> AgentLlmRunSummary:
    total = int(row.total or 0)
    passes = int(row.pass_count or 0)
    partials = int(row.partial_count or 0)
    # Rows with ``status='failed'`` never scored the judge, so their
    # ``verdict`` is NULL and they do NOT contribute to ``fail_count``
    # (which only sums ``verdict == 'FAIL'``). Add them explicitly so the
    # DB-view rates match the in-memory ``_summarize_scored_rows`` shape —
    # otherwise a run with N LLM errors would report ``fail=0`` and an
    # inflated ``pass_rate`` when refetched via ``list_runs`` / ``get_run_detail``.
    failed_status = int(row.failed_status_count or 0)
    fails = int(row.fail_count or 0) + failed_status
    summary = {
        "total": total,
        "pass": passes,
        "partial": partials,
        "fail": fails,
        "pass_rate": (passes / total) if total else 0.0,
        "partial_rate": (partials / total) if total else 0.0,
        "fail_rate": (fails / total) if total else 0.0,
        "duration_ms": int(row.duration_ms or 0),
    }
    status = "failed" if failed_status > 0 else "completed"
    return AgentLlmRunSummary(
        run_id=row.run_id,
        agent_id=row.agent_id,
        run_number=int(row.run_number or 0),
        triggered_by=row.triggered_by,
        judge_model=row.judge_model,
        llm_model=getattr(row, "llm_model", None),
        llm_provider=getattr(row, "llm_provider", None),
        status=status,
        error=None,
        started_at=row.started_at,
        completed_at=row.completed_at,
        summary=summary,
    )


_VERDICT_RANK = {"FAIL": 0, "PARTIAL": 1, "PASS": 2}


def _safe_score(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _diff_agent_llm_runs(
    *,
    baseline_summary: AgentLlmRunSummary,
    candidate_summary: AgentLlmRunSummary,
    baseline_rows: List[dict],
    candidate_rows: List[dict],
    score_drop: float,
) -> dict:
    """Compare two agent-LLM runs' per-scenario rows. Simpler than
    :func:`core.services.evals.eval_service._diff_scored_rows` — agent-LLM
    rows have no retrieval hit and no mapped legacy correctness column —
    but the output shape mirrors it (baseline / candidate / regressions /
    per-question) so the FE renders one compare component for both flavors.

    Regression heuristic per scenario (in order):
    1. Verdict downgrade (``PASS→PARTIAL``, ``PARTIAL→FAIL``, or ``PASS→FAIL``).
    2. Any per-DeepEval-metric score drop ≥ ``score_drop``.
    Both flavors count as regressions; the ``note`` reports the first
    matched signal.
    """
    b_rows = {r["scenario_key"]: r for r in baseline_rows if isinstance(r, dict)}
    c_rows = {r["scenario_key"]: r for r in candidate_rows if isinstance(r, dict)}
    all_keys = sorted(set(b_rows) | set(c_rows))

    per_scenario: List[dict] = []
    regressions: List[dict] = []

    for key in all_keys:
        b = b_rows.get(key)
        c = c_rows.get(key)
        if b is None:
            per_scenario.append(
                {"scenario_key": key, "kind": "new", "candidate_verdict": (c or {}).get("verdict")}
            )
            continue
        if c is None:
            entry = {
                "scenario_key": key,
                "kind": "missing",
                "baseline_verdict": b.get("verdict"),
                "regression": True,
                "note": "scenario removed",
            }
            per_scenario.append(entry)
            regressions.append(entry)
            continue

        b_v = b.get("verdict") or "FAIL"
        c_v = c.get("verdict") or "FAIL"

        b_scores = b.get("metric_scores") or {}
        c_scores = c.get("metric_scores") or {}
        metric_deltas: dict[str, float] = {}
        for metric_name in sorted(set(b_scores) | set(c_scores)):
            b_entry = b_scores.get(metric_name)
            c_entry = c_scores.get(metric_name)
            b_raw = b_entry.get("score") if isinstance(b_entry, dict) else None
            c_raw = c_entry.get("score") if isinstance(c_entry, dict) else None
            if b_raw is None or c_raw is None:
                continue
            metric_deltas[metric_name] = _safe_score(c_raw) - _safe_score(b_raw)

        note: Optional[str] = None
        is_regression = False
        if _VERDICT_RANK.get(c_v, 0) < _VERDICT_RANK.get(b_v, 0):
            note = f"verdict regression {b_v}→{c_v}"
            is_regression = True
        else:
            for metric_name, delta in metric_deltas.items():
                if delta <= -score_drop:
                    note = f"{metric_name} drop {delta:+.2f}"
                    is_regression = True
                    break

        entry = {
            "scenario_key": key,
            "baseline_verdict": b_v,
            "candidate_verdict": c_v,
            "regression": is_regression,
            "note": note,
        }
        for metric_name, delta in metric_deltas.items():
            entry[f"delta_{metric_name}"] = delta
        per_scenario.append(entry)
        if is_regression:
            regressions.append(entry)

    def _pack(summary: AgentLlmRunSummary) -> dict:
        return {
            "id": str(summary.run_id),
            "run_number": summary.run_number,
            "started_at": summary.started_at.isoformat() if summary.started_at else None,
            "summary": summary.summary or {},
        }

    return {
        "baseline": _pack(baseline_summary),
        "candidate": _pack(candidate_summary),
        "score_drop_threshold": score_drop,
        "regressions": regressions,
        "regression_count": len(regressions),
        "per_scenario": per_scenario,
    }


# NOTE: ``AgentLlmEvalRunError`` is intentionally NOT re-exported here — the
# service is fail-soft on scenario errors (they surface as a
# ``AgentLlmRunSummary`` with ``status='failed'``), and only re-raises the
# ``EvalConfigurationError`` / ``AgentLlmEvalConfigError`` pair. Callers that
# want to distinguish those should import them from
# ``core.services.evals.errors`` directly.
__all__ = [
    "AgentLlmEvalService",
    "AgentLlmRunSummary",
    "TRIGGERED_BY_VALUES",
]
