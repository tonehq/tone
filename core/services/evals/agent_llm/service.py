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
from typing import Any, List, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from core.models.agent_llm_eval_result import AgentLlmEvalResult
from core.models.agent_llm_eval_run import AgentLlmEvalRun
from core.services.evals.agent_llm.agent_config_loader import (
    AgentConfigLoader,
    AgentEvalConfig,
)
from core.services.evals.errors import (
    AgentLlmEvalConfigError,
    EvalConfigurationError,
)
from core.services.evals.agent_llm.tool_selection_metric import (
    METRIC_NAME as _TOOL_SELECTION_METRIC,
)
from core.services.llm.chat_complete import (
    ChatCompletion,
    chat_complete,
    chat_complete_with_tools,
)
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
    status: str  # 'completed' | 'failed'
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    # Answer model — the LLM the agent used to answer each scenario. All
    # rows in one run share the same value (config is snapshotted once at
    # run start), so it's safe to include in the grouped summary via a
    # single-value GROUP BY.
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    summary: dict = field(default_factory=dict)
    # Number of scenarios the run will score, stamped at ``begin_pending_run``
    # (known before the worker even picks up the job). Lets the UI render
    # "Scoring N of M" progress while ``status`` is non-terminal without
    # waiting for the results table to catch up.
    total_scenarios: int = 0
    # Number of ``agent_llm_eval_results`` rows already written for this run.
    # Equals ``total_scenarios`` for completed runs; less for in-flight ones;
    # exactly zero for ``pending`` rows. Not stored on the runs table —
    # derived by the ``list_runs`` LEFT JOIN so it stays fresh without a
    # write from the worker each time a row lands.
    scored_count: int = 0
    # Snapshot of the trigger filter (``scenario_ids``, ``tags``, ``folder``,
    # ``folders``) at ``begin_pending_run``. Loose ``dict`` — the UI won't
    # unpack it in v1; kept as a JSONB blob so a future "re-run this exact
    # selection" affordance can round-trip it without a schema change.
    filter_snapshot: Optional[dict] = None


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
        #
        # A scenario with ``expected_tools`` set counts as having a metric
        # (the deterministic ``tool_selection`` one) even if no DeepEval
        # metrics are configured, so a tool-only scenario is legal.
        default_metrics = list(settings.AGENT_LLM_EVAL_METRICS_ENABLED or [])
        for s in scenarios:
            resolved = list(s.metrics or default_metrics)
            if not resolved and not getattr(s, "expected_tools", None):
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
        # When the caller wired us to a runs-table row (FE flow via the
        # router's ``begin_pending_run``), reuse THAT row's ``run_number``
        # so the runs table and the per-scenario results rows agree.
        # Otherwise (CLI / fixture / tests — ``run_id`` is a freshly-minted
        # UUID with no runs-table row) fall back to the historical
        # results-table MAX+1 allocator so those code paths are untouched.
        #
        # If ``run_id`` WAS provided but the runs-table row is missing,
        # something is wrong (row deleted, replica lag, wrong id) — DO
        # NOT silently fall back to the results-table allocator. That
        # would pick a run_number that mismatches the caller's row, so
        # future ``list_runs`` (which joins runs↔results by run_id, not
        # run_number) would still work BUT any historical caller that
        # groups by run_number would see garbage. Refuse loudly instead
        # of persisting inconsistent numbers.
        if run_id is not None:
            existing_number = (
                db.query(AgentLlmEvalRun.run_number)
                .filter(AgentLlmEvalRun.id == run_id)
                .scalar()
            )
            if existing_number is None:
                raise AgentLlmEvalConfigError(
                    f"run_id {run_id} was supplied but no matching row exists "
                    "in agent_llm_eval_runs — refusing to score with a "
                    "divergent run_number."
                )
            next_run_number = int(existing_number)
        else:
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
        folder_id: Optional[UUID] = None,
        folder_ids: Optional[List[UUID]] = None,
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
            folder_id=folder_id,
            folder_ids=folder_ids,
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

    # ── Run lifecycle (agent_llm_eval_runs) ─────────────────────────────
    #
    # These four methods are the ONLY writers to ``agent_llm_eval_runs``.
    # Kept close to ``list_runs`` / ``get_run_detail`` so the read+write
    # surface for run-level state sits together. Follows the shape of
    # ``IngestionRunService.begin_pending_run / mark_running / complete_run /
    # fail_run`` — see ``core/services/ingestion_run_service.py`` for the
    # reference pattern.

    def begin_pending_run(
        self,
        db: Session,
        *,
        organization_id: UUID,
        agent_id: UUID,
        triggered_by: str,
        judge_model: Optional[str],
        judge_engine: Optional[str],
        total_scenarios: int,
        filter_snapshot: Optional[dict] = None,
    ) -> AgentLlmEvalRun:
        """Insert a ``pending`` run row synchronously (called by the router
        BEFORE enqueueing the Procrastinate job) so the UI can render the
        run the moment it's triggered. Allocates ``run_number`` from the
        new runs table's max — historical values were backfilled from
        ``agent_llm_eval_results`` in the migration, so the sequence
        continues without gaps.

        Not idempotent (nothing to key against yet). The router owns the
        one-call-per-click invariant; a duplicate click would create two
        pending rows, which the worker resolves by scoring both — each
        gets its own ``run_id`` and appears as a separate row in the UI.
        """
        if triggered_by not in TRIGGERED_BY_VALUES:
            raise ValueError(
                f"triggered_by must be one of {sorted(TRIGGERED_BY_VALUES)}; "
                f"got {triggered_by!r}"
            )

        # MAX+1 without a lock races under concurrent double-click. A
        # loser INSERT hits ``uq_agent_llm_eval_runs_agent_run_number``
        # and raises IntegrityError. Retry a small number of times with
        # a fresh MAX+1 read after rollback — bounded so a genuinely
        # broken constraint eventually surfaces instead of looping.
        from sqlalchemy.exc import IntegrityError

        last_error: Optional[IntegrityError] = None
        for _attempt in range(3):
            next_number = self._next_run_number_from_runs_table(
                db, agent_id=agent_id, organization_id=organization_id
            )
            run = AgentLlmEvalRun(
                organization_id=organization_id,
                agent_id=agent_id,
                run_number=next_number,
                triggered_by=triggered_by,
                status="pending",
                judge_model=judge_model,
                judge_engine=judge_engine,
                total_scenarios=int(total_scenarios or 0),
                filter_snapshot=filter_snapshot,
            )
            db.add(run)
            try:
                db.commit()
            except IntegrityError as e:
                # Concurrent begin_pending_run took our run_number. Roll
                # back the aborted transaction so ``next_number`` can be
                # re-read cleanly, then try again.
                db.rollback()
                last_error = e
                continue
            db.refresh(run)
            logger.info(
                "[agent-llm-eval] begin_pending_run id={} agent={} run_number={} "
                "total_scenarios={} triggered_by={}",
                run.id, agent_id, run.run_number, run.total_scenarios, triggered_by,
            )
            return run
        # 3 concurrent collisions is not a hot-path scenario — bubble up
        # so the router surfaces a 503 rather than looping forever.
        raise AgentLlmEvalConfigError(
            f"begin_pending_run: could not allocate a unique run_number for "
            f"agent {agent_id} after 3 attempts (concurrent contention)"
        ) from last_error

    def mark_running(
        self,
        db: Session,
        *,
        run_id: UUID,
    ) -> Optional[AgentLlmEvalRun]:
        """Flip a ``pending`` row to ``running`` and stamp ``started_at``.

        Idempotent between ``pending`` and ``running`` (Procrastinate can
        replay a task after a crash and we don't want to clobber
        ``started_at`` on the second attempt).

        Returns:
        - ``None`` when the runs-table row doesn't exist (legacy CLI /
          test callers without a pending row — worker keeps going).
        - The row itself when it flipped or was already ``running``.
        - **The terminal row unchanged when status is ``completed`` /
          ``failed``.** Callers MUST check ``row.status`` and short-circuit
          if terminal — a replay of an already-finished task must NOT
          re-enter scoring (uq_agent_llm_eval_results_run_scenario would
          block the INSERT and the scoring-phase except would flip the
          completed run to ``failed``).
        """
        run = (
            db.query(AgentLlmEvalRun)
            .filter(AgentLlmEvalRun.id == run_id)
            .first()
        )
        if run is None:
            return None
        if run.status == "pending":
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)
        return run

    def complete_run(
        self,
        db: Session,
        *,
        run_id: UUID,
        completed_at: Optional[datetime] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
    ) -> Optional[AgentLlmEvalRun]:
        """Flip a row to ``completed``, stamp ``completed_at``, and
        snapshot the answer-model metadata now that the worker knows the
        agent's live config values. The results table is the source of
        truth for verdict counts, so no summary is stored on this row.

        Returns ``None`` if the runs-table row doesn't exist — same
        legacy-path tolerance as :meth:`mark_running`.
        """
        run = (
            db.query(AgentLlmEvalRun)
            .filter(AgentLlmEvalRun.id == run_id)
            .first()
        )
        if run is None:
            return None
        run.status = "completed"
        run.completed_at = completed_at or datetime.now(timezone.utc)
        run.error = None
        if llm_model is not None:
            run.llm_model = llm_model
        if llm_provider is not None:
            run.llm_provider = llm_provider
        db.commit()
        db.refresh(run)
        return run

    def fail_run(
        self,
        db: Session,
        *,
        run_id: UUID,
        error: str,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
    ) -> Optional[AgentLlmEvalRun]:
        """Flip a row to ``failed`` and stamp a safe, user-visible error
        string. Also snapshots the answer-model metadata if the worker
        got that far before failing. The full traceback belongs in logs
        (``logger.exception`` in the worker) — this column holds only
        what the UI can show.

        Returns ``None`` if the runs-table row doesn't exist — same
        legacy-path tolerance as :meth:`mark_running`.
        """
        run = (
            db.query(AgentLlmEvalRun)
            .filter(AgentLlmEvalRun.id == run_id)
            .first()
        )
        if run is None:
            return None
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        # Cap to keep the column from swallowing a giant repr; the full
        # trace lives in logs anyway.
        run.error = (error or "unknown error")[:2000]
        if llm_model is not None:
            run.llm_model = llm_model
        if llm_provider is not None:
            run.llm_provider = llm_provider
        db.commit()
        db.refresh(run)
        return run

    def _next_run_number_from_runs_table(
        self,
        db: Session,
        *,
        agent_id: UUID,
        organization_id: UUID,
    ) -> int:
        """Per-(agent, org) monotonic run number, read from the NEW runs
        table. Historical numbers were backfilled from the results table
        by the migration, so the sequence never resets.

        Same tolerated-race semantics as :meth:`_next_run_number` — a
        concurrent trigger click could compute the same next value; the
        ``UniqueConstraint(agent_id, run_number)`` on the runs table will
        surface the collision via ``IntegrityError`` (rare enough to
        leave to the caller's retry).
        """
        row = (
            db.query(func.coalesce(func.max(AgentLlmEvalRun.run_number), 0) + 1)
            .filter(
                AgentLlmEvalRun.agent_id == agent_id,
                AgentLlmEvalRun.organization_id == organization_id,
            )
            .scalar()
        )
        return int(row or 1)

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
        organization_id: UUID,
        limit: Optional[int] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[AgentLlmRunSummary], int]:
        """Return ``(summaries, total)`` for one agent (newest first).

        Reads from ``agent_llm_eval_runs`` (the source of truth for run
        lifecycle since the migration to a dedicated runs table). Verdict
        counts / duration come from a small aggregate over
        ``agent_llm_eval_results`` for the CURRENT page's ids only — that
        avoids a giant GROUP BY when the agent has thousands of runs.

        Non-terminal rows (``pending`` / ``running``) surface with zero
        verdict counts and a partial ``scored_count`` — the UI renders a
        "Scoring N of M" progress line for those.

        ``organization_id`` is **required** — every read is tenant-scoped
        so a caller that guesses another tenant's ``agent_id`` can never
        read cross-tenant summaries. Router extracts it from ``JWTClaims``;
        other callers must pass it explicitly.
        """
        # 1. Base query — runs table, newest activity first. Uses
        # ``COALESCE(started_at, created_at)`` so a freshly-created
        # ``pending`` row (started_at IS NULL) lands ABOVE older completed
        # rows — the user's just-triggered run needs to be the first thing
        # they see. Once the worker flips ``pending -> running`` and
        # stamps ``started_at``, the row keeps its position.
        base = (
            db.query(AgentLlmEvalRun)
            .filter(
                AgentLlmEvalRun.agent_id == agent_id,
                AgentLlmEvalRun.organization_id == organization_id,
            )
            .order_by(
                func.coalesce(
                    AgentLlmEvalRun.started_at, AgentLlmEvalRun.created_at
                ).desc(),
                AgentLlmEvalRun.created_at.desc(),
            )
        )

        # 2. Total + page slice.
        total = base.count()
        if page_no is not None or page_size is not None:
            effective_page_no = max(page_no or 1, 1)
            effective_page_size = min(max(page_size or 20, 1), 200)
            offset = (effective_page_no - 1) * effective_page_size
            run_rows = base.offset(offset).limit(effective_page_size).all()
        else:
            run_rows = base.all()

        # 3. Aggregate stats for the current page's run_ids. One extra
        # query bounded by page_size — never grows with total run count.
        stats_by_run = _fetch_run_stats(db, run_ids=[r.id for r in run_rows])

        summaries = [
            _run_and_stats_to_summary(run, stats_by_run.get(run.id))
            for run in run_rows
        ]
        if limit is not None:
            summaries = summaries[:limit]
        return summaries, total

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

        # Prompt-mode: use the agent's ``system_prompt`` as today.
        # Workflow-mode: use the serialized playbook — the SAME text the
        # runtime injects at ``pipeline/service_resolver.py``, so what we
        # score matches what the bot actually runs. The picker lives on the
        # dataclass so the branch stays in ONE place.
        system_content = agent_config.effective_system_prompt
        messages = _build_messages(system_content, scenario.prompt)

        # Tool-aware branch (Phase 2). When the agent has tools attached we
        # use the tool-aware chat call so the LLM can emit tool-call intents
        # instead of (or alongside) text. The tool_calls are captured as
        # ``actual_tools`` and persisted, but NOT executed — the judge
        # deterministic ``tool_selection`` metric grades the intent. Agents
        # with zero tools attached fall through to the exact pre-Phase-2
        # ``chat_complete`` path, byte-identical.
        actual_tools: List[dict] = []
        use_tools = bool(getattr(agent_config, "tools", None))
        try:
            if use_tools:
                completion: ChatCompletion = chat_complete_with_tools(
                    model=agent_config.llm_model,
                    api_key=agent_config.llm_api_key,
                    messages=messages,
                    tools=agent_config.tools,
                    temperature=agent_config.temperature,
                    max_tokens=agent_config.max_tokens,
                )
                actual_answer = completion.content or ""
                actual_tools = [
                    {"name": tc.name, "arguments": tc.arguments}
                    for tc in completion.tool_calls
                ]
            else:
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
                "[agent-llm-eval] agent LLM failed scenario={} model={} use_tools={}",
                scenario.name, agent_config.llm_model, use_tools,
            )
            answer_error = f"{type(e).__name__}: {e}"

        # Judge only when we have an actual answer — a failed LLM call yields
        # an empty string and every metric would trivially FAIL, obscuring
        # the real cause (the LLM error).
        if answer_error is None:
            enabled_metrics = list(
                scenario.metrics or settings.AGENT_LLM_EVAL_METRICS_ENABLED
            )
            # Auto-enable the deterministic tool-selection metric whenever
            # the scenario declares tool expectations — the generator sets
            # both together, so this is the common path. Never appears
            # unless expected_tools is set, so scenarios without tool
            # expectations score exactly as they did in v1.
            if (
                getattr(scenario, "expected_tools", None)
                and _TOOL_SELECTION_METRIC not in enabled_metrics
            ):
                enabled_metrics.append(_TOOL_SELECTION_METRIC)
            threshold = (
                scenario.threshold
                if scenario.threshold is not None
                else settings.EVAL_METRIC_THRESHOLD
            )
            try:
                judge_out = self._judge.judge(
                    prompt=scenario.prompt,
                    system_prompt=system_content,
                    actual_output=actual_answer,
                    api_key=judge_key,
                    model=judge_model,
                    metrics=enabled_metrics,
                    threshold=threshold,
                    expected_output=scenario.expected_answer,
                    persona_criteria=scenario.persona_criteria,
                    instruction_criteria=scenario.instruction_criteria,
                    # Tool-aware inputs (Phase 2). The judge dispatches the
                    # deterministic ``tool_selection`` metric when both are
                    # non-empty; otherwise it silently skips that metric so
                    # text-only scenarios score exactly as they did in v1.
                    expected_tools=getattr(scenario, "expected_tools", None),
                    actual_tools=actual_tools,
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
            "actual_tools": actual_tools,
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
            actual_tools = scored.get("actual_tools") or []
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
                    # Snapshot the folder at run time — matches the tag /
                    # prompt / expected_answer snapshot pattern. Bulk-rename
                    # in ``AgentLlmScenarioService.rename_folder`` updates
                    # this column too so past runs regroup under the new name.
                    "folder": getattr(scenario, "folder", None),
                    "prompt": scenario.prompt,
                    "expected_answer": scenario.expected_answer,
                    "llm_model": agent_config.llm_model,
                    "llm_provider": agent_config.llm_provider,
                    # Stamp the text the LLM actually saw — the playbook for
                    # workflow mode, the raw prompt for prompt mode — so the
                    # results table matches what was scored.
                    "system_prompt": agent_config.effective_system_prompt,
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
                    # Tool-aware fields (Phase 2). ``None`` (not ``[]``) when
                    # the LLM didn't emit any tool calls so the persisted
                    # row visibly distinguishes "no tools attempted" from
                    # "attempted zero tools" for downstream analytics.
                    "tools_called": actual_tools or None,
                    "execution_trace": (
                        {"turns": [{"role": "assistant", "tool_calls": actual_tools}]}
                        if actual_tools
                        else None
                    ),
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
                    "actual_tools": [],
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


def _fetch_run_stats(db: Session, *, run_ids: List[UUID]) -> dict:
    """Aggregate verdict + duration counts for a bounded list of ``run_id``s.
    Returns ``{run_id: row}``; run ids without any results rows (pending /
    running / freshly-triggered) are absent — the caller substitutes zeros
    when composing the summary.

    Bounded by the page size, NOT by total-runs-per-agent, so this stays
    fast even for agents with thousands of historical runs. Falls out to
    a single grouped query against the ``ix_agent_llm_eval_results_run_id``
    index.
    """
    if not run_ids:
        return {}
    rows = (
        db.query(
            AgentLlmEvalResult.run_id.label("run_id"),
            func.count(AgentLlmEvalResult.id).label("scored_count"),
            func.sum(
                case((AgentLlmEvalResult.verdict == "PASS", 1), else_=0)
            ).label("pass_count"),
            func.sum(
                case((AgentLlmEvalResult.verdict == "PARTIAL", 1), else_=0)
            ).label("partial_count"),
            func.sum(
                case((AgentLlmEvalResult.verdict == "FAIL", 1), else_=0)
            ).label("fail_count"),
            # Mutually exclusive with ``fail_count`` on purpose — count
            # only rows where the scorer never reached a verdict
            # (status='failed' AND verdict IS NULL). Without this guard,
            # the old code counted a row that had BOTH verdict='FAIL' and
            # status='failed' twice, letting fail_rate exceed 1.0.
            func.sum(
                case(
                    (
                        (AgentLlmEvalResult.status == "failed")
                        & (AgentLlmEvalResult.verdict.is_(None)),
                        1,
                    ),
                    else_=0,
                )
            ).label("failed_status_count"),
            func.coalesce(func.sum(AgentLlmEvalResult.latency_ms), 0).label(
                "duration_ms"
            ),
        )
        .filter(AgentLlmEvalResult.run_id.in_(list(run_ids)))
        .group_by(AgentLlmEvalResult.run_id)
        .all()
    )
    return {row.run_id: row for row in rows}


def _run_and_stats_to_summary(
    run: AgentLlmEvalRun,
    stats: Optional[Any],
) -> AgentLlmRunSummary:
    """Compose an ``AgentLlmRunSummary`` from a runs-table row + an
    optional aggregate-stats row (``None`` for runs with no scored
    scenarios yet — i.e. ``pending`` / ``running``).

    Field names on the returned dataclass are identical to what the old
    grouped-query path produced, so the API layer, CLI, and existing
    tests keep working. The three new fields (``total_scenarios``,
    ``scored_count``, ``filter_snapshot``) carry the pending-state info
    the FE uses to render the "Scoring N of M" progress line.
    """
    scored_count = int(getattr(stats, "scored_count", 0) or 0)
    passes = int(getattr(stats, "pass_count", 0) or 0)
    partials = int(getattr(stats, "partial_count", 0) or 0)
    failed_status = int(getattr(stats, "failed_status_count", 0) or 0)
    # Same convention as the old ``_row_to_run_summary`` — a scenario that
    # never scored (``status='failed'`` on the results row) counts as a
    # fail so the pass_rate matches ``_summarize_scored_rows``.
    fails = int(getattr(stats, "fail_count", 0) or 0) + failed_status
    duration_ms = int(getattr(stats, "duration_ms", 0) or 0)

    # Denominator uses the total the router stamped (``total_scenarios``),
    # falling back to the count of scored rows for historical runs where
    # the runs-table backfill didn't know the original selection size.
    total_for_rate = int(run.total_scenarios or scored_count)
    summary = {
        "total": total_for_rate,
        "pass": passes,
        "partial": partials,
        "fail": fails,
        "pass_rate": (passes / total_for_rate) if total_for_rate else 0.0,
        "partial_rate": (partials / total_for_rate) if total_for_rate else 0.0,
        "fail_rate": (fails / total_for_rate) if total_for_rate else 0.0,
        "duration_ms": duration_ms,
    }
    return AgentLlmRunSummary(
        run_id=run.id,
        agent_id=run.agent_id,
        run_number=int(run.run_number or 0),
        triggered_by=run.triggered_by,
        judge_model=run.judge_model,
        llm_model=run.llm_model,
        llm_provider=run.llm_provider,
        status=run.status,
        error=run.error,
        started_at=run.started_at,
        completed_at=run.completed_at,
        summary=summary,
        total_scenarios=int(run.total_scenarios or 0),
        scored_count=scored_count,
        filter_snapshot=run.filter_snapshot,
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
