"""EvaluationConfigService — reusable, org-wide judge configs + re-grading.

An *evaluation config* is a saved judge recipe (model + optional custom rubric
prompt + metric set). Running one against a **frozen** ``eval_results`` run
re-judges the exact same answers with a different judge, so results are
comparable across configs (LangSmith's Evaluator→Feedback model). Retrieval and
answer generation are NEVER re-run here — the answers are the fixed source.

Transport-agnostic: methods take a session + plain args. CRUD is called from the
HTTP layer (may raise ``HTTPException`` via ``get_or_404`` for a thin
controller); ``run_config`` runs inside the Procrastinate ``eval`` worker and
raises typed errors / is fail-soft (never HTTP).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models.eval import Eval
from core.models.evaluation_config import EvaluationConfig
from core.models.evaluation_config_result import EvaluationConfigResult
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.evals.deepeval.metric_registry import (
    AGENT_CONTEXT_METRICS,
    CONVERSATION_METRICS,
    SUPPORTED_METRICS,
)
from core.services.evals.errors import EvalNotFoundError, EvalRunError
from core.services.evals.eval_service import EvalService, _require_llm_key
from core.services.evals.judge_factory import build_judge_service
from core.services.org_settings import load_eval_settings_for_org

# The judge engine that supports a custom rubric prompt (GEval criteria).
_DEEPEVAL = "deepeval"

# The GEval metric that carries a config's custom rubric prompt.
_CUSTOM_PROMPT_METRIC = "correctness"

# Metrics valid for the single-turn RAG judge: every registered metric minus the
# ones the RAG judge rejects (agent-context GEval + conversation-native). Kept in
# sync with ``DeepEvalJudgeService.judge`` by construction (same source sets).
RAG_SAFE_METRICS: frozenset[str] = frozenset(
    SUPPORTED_METRICS.keys()
) - AGENT_CONTEXT_METRICS - CONVERSATION_METRICS

_SORT_MAP = {
    "name": EvaluationConfig.name,
    "created_at": EvaluationConfig.created_at,
    "updated_at": EvaluationConfig.updated_at,
}


class EvaluationConfigService(BaseService):
    # ── CRUD ──────────────────────────────────────────────────────────────
    def create_config(
        self,
        *,
        name: str,
        judge_model: str,
        judge_engine: str = _DEEPEVAL,
        judge_prompt: Optional[str] = None,
        description: Optional[str] = None,
        metrics_enabled: Optional[List[str]] = None,
        metric_threshold: Optional[float] = None,
        metric_thresholds: Optional[dict] = None,
        is_default: bool = False,
    ) -> EvaluationConfig:
        # Default the metric set from the org's RAG eval settings so an unset
        # config mirrors what the normal eval run would use.
        if metrics_enabled is None:
            metrics_enabled = list(
                load_eval_settings_for_org(self.db, self.org_id).metrics_enabled
            )
        clean = self._validate(
            name=name,
            judge_model=judge_model,
            judge_engine=judge_engine,
            judge_prompt=judge_prompt,
            metrics_enabled=metrics_enabled,
            metric_threshold=metric_threshold,
            metric_thresholds=metric_thresholds,
            exclude_id=None,
        )
        config = EvaluationConfig(
            organization_id=self.org_id,
            name=clean["name"],
            description=description,
            judge_model=clean["judge_model"],
            judge_engine=clean["judge_engine"],
            judge_prompt=clean["judge_prompt"],
            metrics_enabled=clean["metrics_enabled"],
            metric_threshold=clean["metric_threshold"],
            metric_thresholds=clean["metric_thresholds"],
            is_default=False,
        )
        self.db.add(config)
        self.db.flush()
        if is_default:
            self._apply_default(config.id)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_config(self, config_id: Any, **patch: Any) -> EvaluationConfig:
        config = self.get_config(config_id)
        # Merge current values so partial patches validate against the full row.
        merged = {
            "name": patch.get("name", config.name),
            "judge_model": patch.get("judge_model", config.judge_model),
            "judge_engine": patch.get("judge_engine", config.judge_engine),
            "judge_prompt": patch.get("judge_prompt", config.judge_prompt),
            "metrics_enabled": patch.get("metrics_enabled", config.metrics_enabled),
            "metric_threshold": patch.get("metric_threshold", config.metric_threshold),
            "metric_thresholds": patch.get(
                "metric_thresholds", config.metric_thresholds
            ),
        }
        clean = self._validate(exclude_id=config.id, **merged)
        config.name = clean["name"]
        config.judge_model = clean["judge_model"]
        config.judge_engine = clean["judge_engine"]
        config.judge_prompt = clean["judge_prompt"]
        config.metrics_enabled = clean["metrics_enabled"]
        config.metric_threshold = clean["metric_threshold"]
        config.metric_thresholds = clean["metric_thresholds"]
        if "description" in patch:
            config.description = patch["description"]
        if patch.get("is_default") is True:
            self._apply_default(config.id)
        self.db.commit()
        self.db.refresh(config)
        return config

    def list_configs(
        self,
        *,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        page_no: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[EvaluationConfig], int]:
        q = self.query(EvaluationConfig).filter(
            EvaluationConfig.is_active.is_(True)
        )
        return apply_search_sort_pagination(
            q,
            search=search,
            search_fields=[EvaluationConfig.name, EvaluationConfig.description],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map=_SORT_MAP,
            page_no=page_no,
            page_size=page_size,
        )

    def get_config(self, config_id: Any) -> EvaluationConfig:
        return self.get_or_404(EvaluationConfig, config_id, name="Evaluation config")

    def delete_config(self, config_id: Any) -> None:
        config = self.get_config(config_id)
        config.is_active = False
        config.deleted_at = datetime.now(timezone.utc)
        config.is_default = False
        self.db.commit()

    def set_default(self, config_id: Any) -> EvaluationConfig:
        config = self.get_config(config_id)
        self._apply_default(config.id)
        self.db.commit()
        self.db.refresh(config)
        return config

    def _apply_default(self, config_id: Any) -> None:
        """Atomically make exactly one config the org default — clear the flag
        on every other row, set it on this one (single UPDATE each, no
        read-check-write race)."""
        self.query(EvaluationConfig).filter(
            EvaluationConfig.id != config_id
        ).update({EvaluationConfig.is_default: False}, synchronize_session=False)
        self.query(EvaluationConfig).filter(
            EvaluationConfig.id == config_id
        ).update({EvaluationConfig.is_default: True}, synchronize_session=False)

    # ── Validation ────────────────────────────────────────────────────────
    def _validate(
        self,
        *,
        name: str,
        judge_model: str,
        judge_engine: str,
        judge_prompt: Optional[str],
        metrics_enabled: Any,
        metric_threshold: Optional[float],
        metric_thresholds: Optional[dict],
        exclude_id: Optional[Any],
    ) -> dict:
        name = (name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name is required.")
        if not (judge_model or "").strip():
            raise HTTPException(status_code=400, detail="Judge model is required.")

        engine = (judge_engine or _DEEPEVAL).strip().lower()

        metrics = [str(m).strip() for m in (metrics_enabled or []) if str(m).strip()]
        metrics = list(dict.fromkeys(metrics))  # de-dupe, keep order
        bad = [m for m in metrics if m not in RAG_SAFE_METRICS]
        if bad:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported metric(s) for RAG judging: {bad}. "
                    f"Allowed: {sorted(RAG_SAFE_METRICS)}"
                ),
            )

        prompt = (judge_prompt or "").strip() or None
        if prompt is not None:
            # A custom prompt is a GEval rubric — only the deepeval engine's
            # ``correctness`` metric carries it. Force the engine and ensure the
            # carrier metric is enabled so the prompt actually takes effect.
            if engine != _DEEPEVAL:
                raise HTTPException(
                    status_code=400,
                    detail="A custom judge prompt requires the 'deepeval' engine.",
                )
            if _CUSTOM_PROMPT_METRIC not in metrics:
                metrics.append(_CUSTOM_PROMPT_METRIC)

        if not metrics:
            raise HTTPException(
                status_code=400,
                detail="Enable at least one metric (or provide a custom prompt).",
            )

        threshold = metric_threshold if metric_threshold is not None else 0.7
        if not (0.0 < float(threshold) <= 1.0):
            raise HTTPException(
                status_code=400,
                detail="metric_threshold must be in (0, 1].",
            )

        overrides: dict = {}
        if isinstance(metric_thresholds, dict):
            for k, v in metric_thresholds.items():
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    continue
                if 0.0 < float(v) <= 1.0:
                    overrides[str(k)] = float(v)

        # Name unique per org among live rows (DB enforces it too; this gives a
        # friendly 400 instead of a 500 on the IntegrityError).
        dupe_q = self.query(EvaluationConfig).filter(
            EvaluationConfig.is_active.is_(True),
            func.lower(EvaluationConfig.name) == name.lower(),
        )
        if exclude_id is not None:
            dupe_q = dupe_q.filter(EvaluationConfig.id != exclude_id)
        if dupe_q.first() is not None:
            raise HTTPException(
                status_code=400,
                detail=f"An evaluation config named {name!r} already exists.",
            )

        return {
            "name": name,
            "judge_model": judge_model.strip(),
            "judge_engine": engine,
            "judge_prompt": prompt,
            "metrics_enabled": metrics,
            "metric_threshold": float(threshold),
            "metric_thresholds": overrides,
        }

    # ── Run (worker-side; no HTTP) ────────────────────────────────────────
    def run_config(
        self,
        db: Session,
        *,
        source_run_id: Any,
        evaluation_config_id: Any,
        triggered_by: str = "manual",
    ) -> dict:
        """Re-judge a frozen source run's answers with one config.

        Runs inside the ``eval`` worker. Reads everything up front (config,
        frozen rows, judge key), runs the judge loop without holding the
        session, then bulk-inserts on a fresh session. Fail-soft per row.
        """
        config = (
            self.query(EvaluationConfig)
            .filter(
                EvaluationConfig.id == evaluation_config_id,
                EvaluationConfig.is_active.is_(True),
            )
            .first()
        )
        if config is None:
            raise EvalNotFoundError(
                f"Evaluation config {evaluation_config_id} not found"
            )

        org_id = config.organization_id
        rows = EvalService().get_scored_rows_for_run(
            db, run_id=source_run_id, org_id=org_id
        )
        if not rows:
            raise EvalRunError(
                f"Source run {source_run_id} has no scored answers to re-judge"
            )

        judge_key = _require_llm_key(db, org_id, config.judge_model)

        # Snapshot the fields the loop needs; the loop below does network I/O.
        judge_model = config.judge_model
        judge_engine = config.judge_engine
        metrics_enabled = list(config.metrics_enabled or [])
        metric_threshold = config.metric_threshold
        criteria = (
            {_CUSTOM_PROMPT_METRIC: config.judge_prompt}
            if config.judge_prompt and judge_engine == _DEEPEVAL
            else None
        )

        judge = build_judge_service(
            engine=judge_engine,
            metrics_enabled=metrics_enabled,
            metric_threshold=metric_threshold,
        )

        next_number = int(
            db.query(
                func.coalesce(func.max(EvaluationConfigResult.config_run_number), 0)
                + 1
            )
            .filter(
                EvaluationConfigResult.evaluation_config_id == evaluation_config_id,
                EvaluationConfigResult.source_run_id == source_run_id,
            )
            .scalar()
        )
        config_run_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)

        persisted: List[dict] = []
        completed = 0
        for row in rows:
            row_started = time.monotonic()
            status = "completed"
            judge_result: dict = {}
            try:
                judge_kwargs = dict(
                    question=row.get("question") or "",
                    expected_answer=row.get("expected_answer") or "",
                    actual_answer=row.get("actual_answer") or "",
                    retrieved_chunks=row.get("retrieved_chunks") or [],
                    api_key=judge_key,
                    model=judge_model,
                )
                if criteria is not None:
                    judge_kwargs["criteria"] = criteria
                judge_result = judge.judge(**judge_kwargs)
                completed += 1
            except Exception:
                logger.exception(
                    "[eval-config] judge failed config_run_id=%s eval_id=%s",
                    config_run_id,
                    row.get("eval_id"),
                )
                status = "failed"
            latency_ms = int((time.monotonic() - row_started) * 1000)
            persisted.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": org_id,
                    "evaluation_config_id": evaluation_config_id,
                    "source_run_id": source_run_id,
                    "eval_id": row.get("eval_id"),
                    "config_run_id": config_run_id,
                    "config_run_number": next_number,
                    "triggered_by": triggered_by,
                    "status": status,
                    "verdict": judge_result.get("verdict"),
                    "judge_reasoning": judge_result.get("reasoning"),
                    "metric_scores": judge_result.get("metric_scores"),
                    "latency_ms": latency_ms,
                    "started_at": started_at,
                    "completed_at": datetime.now(timezone.utc),
                }
            )

        from core.database.session import SessionLocal

        with SessionLocal() as fresh:
            fresh.bulk_insert_mappings(EvaluationConfigResult, persisted)
            fresh.commit()

        logger.info(
            "[eval-config] persisted config_run_id={} rows={} completed={} failed={}",
            config_run_id,
            len(persisted),
            completed,
            len(persisted) - completed,
        )
        return {
            "config_run_id": str(config_run_id),
            "config_run_number": next_number,
            "source_run_id": str(source_run_id),
            "evaluation_config_id": str(evaluation_config_id),
            "total": len(persisted),
            "completed": completed,
            "failed": len(persisted) - completed,
        }

    # ── Read: results + compare ───────────────────────────────────────────
    def list_results(
        self,
        *,
        source_run_id: Any,
        config_run_ids: Optional[List[Any]] = None,
    ) -> List[dict]:
        """Rows for a source run (optionally limited to specific config passes),
        joined to their question, org-scoped."""
        q = (
            self.query(EvaluationConfigResult)
            .filter(EvaluationConfigResult.source_run_id == source_run_id)
        )
        if config_run_ids:
            q = q.filter(
                EvaluationConfigResult.config_run_id.in_(list(config_run_ids))
            )
        rows = q.order_by(
            EvaluationConfigResult.config_run_number.desc()
        ).all()
        return [r.to_dict() for r in rows]

    def list_config_runs(self, *, source_run_id: Any) -> List[dict]:
        """One summary row per config pass against this source run (for the
        run/compare picker): config id, run number, counts + verdict tally."""
        rows = (
            self.query(EvaluationConfigResult)
            .filter(EvaluationConfigResult.source_run_id == source_run_id)
            .all()
        )
        by_pass: dict = {}
        for r in rows:
            key = str(r.config_run_id)
            agg = by_pass.setdefault(
                key,
                {
                    "config_run_id": key,
                    "evaluation_config_id": (
                        str(r.evaluation_config_id)
                        if r.evaluation_config_id
                        else None
                    ),
                    "config_run_number": r.config_run_number,
                    "source_run_id": str(r.source_run_id),
                    "total": 0,
                    "verdicts": {},
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                },
            )
            agg["total"] += 1
            v = (r.verdict or "UNKNOWN").upper()
            agg["verdicts"][v] = agg["verdicts"].get(v, 0) + 1
        return sorted(
            by_pass.values(),
            key=lambda a: a["config_run_number"],
            reverse=True,
        )
