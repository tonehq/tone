"""Agent LLM (Level-2) eval routes — CRUD for scenarios and orchestration
for runs. Every path is org-scoped through :func:`require_org_member`; the
service layer double-checks by scoping every SQL read to the caller's org.

The router lives in one file (not the two-edition ``knowledge_base_routes``
builder pattern) because agent-LLM eval routes have no EE-vs-Core diff —
same auth dep, same service, same response shapes. Mounted in both
editions from ``main.py``.
"""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.models.agent import Agent
from core.services.evals.agent_llm.scenario_service import (
    AgentLlmScenarioService,
    ScenarioInput,
    ScenarioPatch,
)
from core.services.evals.agent_llm.service import AgentLlmEvalService
from core.services.evals.errors import (
    AgentLlmEvalConfigError,
    AgentLlmScenarioKeyConflictError,
    AgentLlmScenarioNotFoundError,
    EvalConfigurationError,
)
from core.services.ingestion_queue import enqueue_agent_llm_eval_sync
from shared.config import settings

router = APIRouter()


# ── Pydantic request bodies ─────────────────────────────────────────────


class ListScenariosRequest(BaseModel):
    """POST body for ``/{agent_id}/llm-evals/scenarios/list`` — matches the
    project's standard ``POST /list`` convention (search + tag filter +
    folder filter + whitelisted sort + pagination).

    ``folder`` is exact-match: a value matches that named folder; an
    empty string matches "Uncategorized" (NULL folder); ``None`` skips.
    """

    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    folder: Optional[str] = Field(default=None, max_length=120)
    # Exact-match filter against ``AgentLlmEvalScenario.source``. Bounded
    # to the whitelisted set so a caller can't sneak arbitrary values into
    # the SQL. Any unlisted value is silently ignored by the service
    # (skip-filter semantics — matches the ``folder`` / ``tags`` behavior
    # for consistency).
    source: Optional[str] = Field(
        default=None, pattern="^(manual|csv|generated|fixture)$"
    )
    sort_by: Optional[str] = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class ScenarioIn(BaseModel):
    """Shared body for POST /scenarios and each item of POST /scenarios/bulk.

    ``scenario_key`` collision (against existing rows OR within the same
    bulk payload) yields ``409 SCENARIO_KEY_CONFLICT``. Empty
    ``prompt`` / ``scenario_key`` are rejected at the service (400).
    """

    scenario_key: str = Field(..., min_length=1, max_length=120)
    prompt: str = Field(..., min_length=1)
    expected_answer: Optional[str] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: Optional[List[str]] = None
    folder: Optional[str] = Field(default=None, max_length=120)
    metrics_override: Optional[List[str]] = None
    threshold_override: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    scenario_ord: Optional[int] = Field(default=None, ge=0)


class ScenariosBulkRequest(BaseModel):
    scenarios: List[ScenarioIn] = Field(..., min_length=1)
    # Optional client attribution — defaults to ``'manual'`` for the
    # normal bulk-create flow. The Auto-generate preview persists with
    # ``'generated'`` after the user confirms the picks so the source
    # badge in the scenarios table reflects reality. Whitelisted so a
    # caller can't invent arbitrary values (``'csv'`` and ``'fixture'``
    # stay owned by their respective server-side flows).
    source: Optional[str] = Field(default=None, pattern="^(manual|generated)$")


class ScenarioPatchRequest(BaseModel):
    """PATCH-style body for PUT /scenarios/{id}. Every field is optional;
    passing ``threshold_override: -1`` clears the override so the resolver
    falls back to the org's ``agent_llm.metric_threshold``."""

    scenario_key: Optional[str] = Field(default=None, min_length=1, max_length=120)
    prompt: Optional[str] = Field(default=None, min_length=1)
    expected_answer: Optional[str] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: Optional[List[str]] = None
    folder: Optional[str] = Field(default=None, max_length=120)
    metrics_override: Optional[List[str]] = None
    threshold_override: Optional[float] = None
    scenario_ord: Optional[int] = Field(default=None, ge=0)


class GenerateScenariosRequest(BaseModel):
    """POST /scenarios/generate. ``dry_run=True`` (the default) returns a
    preview without persisting; ``dry_run=False`` bulk-creates with
    ``source='generated'`` using the SAME code path as manual create."""

    strategy: str = Field(default="noop", min_length=1)
    count: int = Field(default=10, ge=1, le=100)
    dry_run: bool = Field(default=True)
    options: Optional[dict] = None
    # When set, every persisted (non-dry-run) scenario is stamped with
    # this folder. Ignored on dry-run previews.
    folder: Optional[str] = Field(default=None, max_length=120)


class TriggerRunRequest(BaseModel):
    """POST /runs — enqueue a Procrastinate job to score the agent."""

    scenario_ids: Optional[List[UUID]] = None
    tags: Optional[List[str]] = None
    # Restrict the run to one folder (empty string = Uncategorized).
    folder: Optional[str] = Field(default=None, max_length=120)
    # Multi-select variant of ``folder`` — matches ANY of the folders in the
    # list. Each entry follows the same rule as ``folder``: '' = Uncategorized,
    # any other string = that named folder. When both ``folder`` and
    # ``folders`` are provided the service treats ``folders`` as the source
    # of truth and ignores ``folder`` (they never silently AND-combine).
    folders: Optional[List[str]] = None
    judge_model: Optional[str] = Field(default=None, min_length=1)


class RenameFolderRequest(BaseModel):
    """POST /folders/rename body."""

    old_name: str = Field(..., min_length=1, max_length=120)
    new_name: str = Field(..., min_length=1, max_length=120)


class DeleteFolderRequest(BaseModel):
    """POST /folders/delete body. ``name`` must be a real folder name —
    the virtual ``Uncategorized`` bucket (rows with ``folder IS NULL``) is
    not deletable as a group; the service raises 400 for empty names."""

    name: str = Field(..., min_length=1, max_length=120)


class DeleteScenariosBulkRequest(BaseModel):
    """POST /scenarios/bulk_delete body. Ids that don't belong to the
    caller's (agent, org) are silently skipped by the service — so a
    stale UI cache with a since-deleted id doesn't 404 the whole batch.

    Capped at 500 ids per call so a runaway client can't push a giant
    ``WHERE id IN (…)`` past PG's 65535-parameter limit or make the
    planner unhappy. A legitimate "delete every scenario in the folder"
    flow already has a dedicated ``/folders/delete`` endpoint."""

    scenario_ids: List[UUID] = Field(..., min_length=1, max_length=500)


class CompareRunsRequest(BaseModel):
    baseline_run_id: UUID
    candidate_run_id: UUID
    score_drop: float = Field(default=0.15, gt=0.0, le=1.0)


# ── Helpers ─────────────────────────────────────────────────────────────


def _resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


def _ensure_agent_in_org(db: Session, org_id: UUID, agent_id: UUID) -> UUID:
    """Verify ``agent_id`` belongs to the caller's org AND is not soft-deleted
    — otherwise a forged URL could still hit the scenario service, and a
    tombstoned agent would silently accept CRUD + eval runs. Fail fast at
    the route boundary."""
    exists = (
        db.query(Agent.id)
        .filter(
            Agent.id == agent_id,
            Agent.organization_id == org_id,
            Agent.deleted_at.is_(None),
        )
        .first()
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return agent_id


def _scenario_input_from_body(body: ScenarioIn) -> ScenarioInput:
    return ScenarioInput(
        scenario_key=body.scenario_key,
        prompt=body.prompt,
        expected_answer=body.expected_answer,
        persona_criteria=body.persona_criteria,
        instruction_criteria=body.instruction_criteria,
        tags=body.tags,
        folder=body.folder,
        metrics_override=body.metrics_override,
        threshold_override=body.threshold_override,
        scenario_ord=body.scenario_ord,
    )


def _scenario_patch_from_body(body: ScenarioPatchRequest) -> ScenarioPatch:
    return ScenarioPatch(
        scenario_key=body.scenario_key,
        prompt=body.prompt,
        expected_answer=body.expected_answer,
        persona_criteria=body.persona_criteria,
        instruction_criteria=body.instruction_criteria,
        tags=body.tags,
        folder=body.folder,
        metrics_override=body.metrics_override,
        threshold_override=body.threshold_override,
        scenario_ord=body.scenario_ord,
    )


def _run_summary_to_dict(s) -> dict:
    return {
        "run_id": str(s.run_id),
        "agent_id": str(s.agent_id),
        "run_number": s.run_number,
        "triggered_by": s.triggered_by,
        "judge_model": s.judge_model,
        # Answer model — the agent's LLM at the time of the run. Snapshotted
        # by ``mark_running`` / ``complete_run`` when the worker has loaded
        # the live agent config.
        "llm_model": getattr(s, "llm_model", None),
        "llm_provider": getattr(s, "llm_provider", None),
        "status": s.status,
        "error": s.error,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "summary": s.summary or {},
        # Run-lifecycle fields (agent_llm_eval_runs). ``getattr`` fallbacks
        # keep the response schema-stable if a caller ever hands us the
        # legacy dataclass shape (e.g. from an in-memory ``run_eval`` CLI
        # path that hasn't been wired to the runs table).
        "total_scenarios": int(getattr(s, "total_scenarios", 0) or 0),
        "scored_count": int(getattr(s, "scored_count", 0) or 0),
        "filter_snapshot": getattr(s, "filter_snapshot", None),
    }


# Any typed service error → HTTP mapping. Kept next to the router so the
# same shape is used across every handler (no per-route try/except drift).


def _handle_scenario_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AgentLlmScenarioNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCENARIO_NOT_FOUND", "message": str(exc)},
        )
    if isinstance(exc, AgentLlmScenarioKeyConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SCENARIO_KEY_CONFLICT", "message": str(exc)},
        )
    if isinstance(exc, AgentLlmEvalConfigError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AGENT_EVAL_CONFIG_INVALID", "message": str(exc)},
        )
    if isinstance(exc, EvalConfigurationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EVAL_CONFIG_INVALID", "message": str(exc)},
        )
    # Not one we own — bubble up as-is; global handler covers 500.
    raise exc


# ── Scenario routes ─────────────────────────────────────────────────────


@router.post("/agents/{agent_id}/llm-evals/scenarios/list")
def list_llm_eval_scenarios(
    agent_id: UUID,
    body: ListScenariosRequest = Body(default=None),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Paginated list of scenarios for one agent. Follows the project's
    canonical ``POST /list`` shape so the FE can reuse ``CustomTable``
    server-side sort/search/pagination without a special case."""
    payload = body or ListScenariosRequest()
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    rows, total = svc.list_scenarios(
        agent_id,
        search=payload.search,
        tags=payload.tags,
        folder=payload.folder,
        source=payload.source,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        page_no=payload.page_no,
        page_size=payload.page_size,
    )
    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page_no": payload.page_no,
        "page_size": payload.page_size,
    }


@router.post(
    "/agents/{agent_id}/llm-evals/scenarios",
    status_code=status.HTTP_201_CREATED,
)
def create_llm_eval_scenario(
    agent_id: UUID,
    body: ScenarioIn = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create one scenario. Returns the persisted row so the FE can drop it
    straight into its cache without a refetch."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        row = svc.create_scenario(agent_id, _scenario_input_from_body(body))
    except (
        AgentLlmScenarioKeyConflictError,
        AgentLlmScenarioNotFoundError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e
    return row.to_dict()


@router.post(
    "/agents/{agent_id}/llm-evals/scenarios/bulk",
    status_code=status.HTTP_201_CREATED,
)
def create_llm_eval_scenarios_bulk(
    agent_id: UUID,
    body: ScenariosBulkRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Bulk-create scenarios in one transaction. Any duplicate ``scenario_key``
    (in the payload OR against existing rows) aborts the whole batch —
    no partial writes."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    payloads = [_scenario_input_from_body(s) for s in body.scenarios]
    try:
        rows = svc.create_scenarios_bulk(
            agent_id, payloads, source=body.source or "manual"
        )
    except (
        AgentLlmScenarioKeyConflictError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e
    return {"items": [r.to_dict() for r in rows], "created": len(rows)}


@router.post(
    "/agents/{agent_id}/llm-evals/scenarios/upload-csv",
    status_code=status.HTTP_201_CREATED,
)
async def upload_llm_eval_scenarios_csv(
    agent_id: UUID,
    file: UploadFile = File(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Parse a CSV upload → create scenarios with ``source='csv'``. Row
    validation (empty prompt, duplicate keys) uses the SAME checks as the
    manual create path — one implementation of the rules."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    try:
        raw = await file.read()
    finally:
        await file.close()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        rows = svc.import_from_csv(agent_id, raw)
    except (
        AgentLlmScenarioKeyConflictError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e
    return {"items": [r.to_dict() for r in rows], "created": len(rows)}


@router.put("/agents/{agent_id}/llm-evals/scenarios/{scenario_id}")
def update_llm_eval_scenario(
    agent_id: UUID,
    scenario_id: UUID,
    body: ScenarioPatchRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """PATCH-style update — fields left unset on the body are not touched.
    ``threshold_override: -1`` is the sentinel to clear the override."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        row = svc.update_scenario(
            agent_id, scenario_id, _scenario_patch_from_body(body)
        )
    except (
        AgentLlmScenarioNotFoundError,
        AgentLlmScenarioKeyConflictError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e
    return row.to_dict()


@router.delete(
    "/agents/{agent_id}/llm-evals/scenarios/{scenario_id}",
    status_code=status.HTTP_200_OK,
)
def delete_llm_eval_scenario(
    agent_id: UUID,
    scenario_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Hard-delete one scenario. Historical run results retain their own
    snapshotted prompt/expected_answer so past runs remain fully readable."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        svc.delete_scenario(agent_id, scenario_id)
    except AgentLlmScenarioNotFoundError as e:
        raise _handle_scenario_error(e) from e
    return {"deleted": str(scenario_id)}


@router.post("/agents/{agent_id}/llm-evals/scenarios/bulk_delete")
def delete_llm_eval_scenarios_bulk(
    agent_id: UUID,
    body: DeleteScenariosBulkRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Hard-delete every scenario in ``scenario_ids`` that belongs to
    ``agent_id``. Ids not in this (agent, org) are silently skipped so
    a stale UI cache doesn't 404 the whole batch. Response's
    ``deleted`` count lets the FE quote the exact number in its toast."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    deleted = svc.delete_scenarios_bulk(agent_id, body.scenario_ids)
    return {"deleted": deleted, "requested": len(body.scenario_ids)}


@router.post("/agents/{agent_id}/llm-evals/scenarios/generate")
def generate_llm_eval_scenarios(
    agent_id: UUID,
    body: GenerateScenariosRequest = Body(default=None),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Ask the given strategy for ``count`` scenarios. In v1 the only
    registered strategy is ``noop``, so this route returns
    ``{"generated": [], "strategy": "noop", "note": ...}``. Adding a real
    strategy in the future only requires a new file under
    ``scenario_generation/strategies/`` — this route is unchanged.
    """
    payload = body or GenerateScenariosRequest()
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        batch = svc.generate_scenarios(
            agent_id,
            strategy=payload.strategy,
            count=payload.count,
            dry_run=payload.dry_run,
            options=payload.options,
            folder=payload.folder,
        )
    except ValueError as e:
        # Unknown strategy — the factory raises ValueError, mapped to 400.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNKNOWN_STRATEGY", "message": str(e)},
        ) from e
    except (
        AgentLlmScenarioKeyConflictError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e
    return {
        "strategy": batch.strategy,
        "dry_run": payload.dry_run,
        "generated": [
            {
                "scenario_key": g.scenario_key,
                "prompt": g.prompt,
                "expected_answer": g.expected_answer,
                "persona_criteria": g.persona_criteria,
                "instruction_criteria": g.instruction_criteria,
                "tags": list(g.tags or []),
                "confidence": g.confidence,
                "generation_metadata": g.generation_metadata,
            }
            for g in batch.generated
        ],
        "persisted": [r.to_dict() for r in batch.persisted],
        "note": batch.note,
    }


# ── Run routes ──────────────────────────────────────────────────────────


@router.post(
    "/agents/{agent_id}/llm-evals/runs",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_llm_eval_run(
    agent_id: UUID,
    body: TriggerRunRequest = Body(default=None),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Enqueue an agent-LLM eval batch. Returns immediately with a job id —
    the worker picks it up on the ``agent_eval`` queue. Fast pre-flight
    check (agent exists, at least one scenario, valid triggered_by) so an
    empty click doesn't queue a doomed job."""
    payload = body or TriggerRunRequest()
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)

    # Reject early if there are zero scenarios — otherwise the worker task
    # would burn a wake-up cycle only to raise ``AgentLlmEvalConfigError``
    # and log a scary "run failed" line.
    svc = AgentLlmScenarioService(db, org_id=org_id)
    rows = svc.load_all_for_run(
        agent_id,
        scenario_ids=payload.scenario_ids,
        tags=payload.tags,
        folder=payload.folder,
        folders=payload.folders,
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_SCENARIOS",
                "message": (
                    "No scenarios matched — create scenarios (or drop the folder / tag / id "
                    "filters) before running an eval."
                ),
            },
        )

    # This route is only reached from the FE "Run Eval" button — every run
    # queued through here is stamped ``'manual'``. Programmatic integrations
    # can bump this by extending ``TriggerRunRequest`` with a bounded
    # ``triggered_by`` enum; until then the literal keeps the audit trail
    # consistent with the RAG-eval ``'manual'`` triggers.
    triggered_by = "manual"

    # Resolve the judge model here so the pending row surfaces the correct
    # value in the UI from the moment it appears — mirrors the resolution
    # the worker's ``run_eval`` does at line ~183 (org override → env →
    # hardcoded default). Explicit caller value still wins.
    if payload.judge_model:
        resolved_judge_model = payload.judge_model
    else:
        from core.services.org_settings import load_agent_llm_eval_settings_for_org

        resolved_judge_model = load_agent_llm_eval_settings_for_org(db, org_id).judge_model

    # 1. Insert the pending run row SYNCHRONOUSLY so the FE's runs list
    # shows the row the moment the invalidator fires — no more "click Run
    # and stare at nothing while the worker warms up" gap.
    eval_svc = AgentLlmEvalService()
    run_row = eval_svc.begin_pending_run(
        db,
        organization_id=org_id,
        agent_id=agent_id,
        triggered_by=triggered_by,
        judge_model=resolved_judge_model,
        judge_engine="deepeval",
        total_scenarios=len(rows),
        filter_snapshot={
            "scenario_ids": (
                [str(s) for s in payload.scenario_ids] if payload.scenario_ids else None
            ),
            "tags": payload.tags,
            "folder": payload.folder,
            "folders": payload.folders,
        },
    )

    # 2. Enqueue the Procrastinate job, forwarding ``run_id`` so the
    # worker's ``mark_running`` / ``complete_run`` / ``fail_run`` calls
    # target the same row. Forwards the ALREADY-RESOLVED ``judge_model``
    # (not the raw ``payload.judge_model``) so a mid-request org-settings
    # change can't desync the runs-table row's ``judge_model`` snapshot
    # from what the worker actually uses to score. The worker's own
    # resolver stays as a fallback for legacy CLI callers that don't
    # pre-resolve.
    try:
        job_id = enqueue_agent_llm_eval_sync(
            agent_id,
            triggered_by=triggered_by,
            scenario_ids=payload.scenario_ids,
            tags=payload.tags,
            folder=payload.folder,
            folders=payload.folders,
            judge_model=resolved_judge_model,
            run_id=str(run_row.id),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "[agent-llm-eval] enqueue failed agent={} org={} run_id={}",
            agent_id, org_id, run_row.id,
        )
        # Flip the pending row to ``failed`` so the UI shows the failure
        # instead of a phantom row that never transitions.
        try:
            eval_svc.fail_run(db, run_id=run_row.id, error="enqueue_failed")
        except Exception:  # noqa: BLE001
            logger.exception(
                "[agent-llm-eval] fail_run cleanup failed run_id={}", run_row.id
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ENQUEUE_FAILED", "message": str(e)},
        ) from e

    return {
        "job_id": job_id,
        "run_id": str(run_row.id),
        "status": "pending",
        "triggered_by": triggered_by,
    }


@router.get("/agents/{agent_id}/llm-evals/runs")
def list_llm_eval_runs(
    agent_id: UUID,
    page_no: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=200),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Every run for one agent, newest first. Grouped by ``run_id`` at the
    SQL layer so N scenarios → 1 summary row.

    Pagination is optional and backward-compatible: callers that omit
    ``page_no`` / ``page_size`` get every run (as before). Callers that pass
    either get the requested page. The response always includes ``total``
    so a paginated client can render page counts without a second request.
    """
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmEvalService()
    summaries, total = svc.list_runs(
        db,
        agent_id=agent_id,
        organization_id=org_id,
        page_no=page_no,
        page_size=page_size,
    )
    return {
        "items": [_run_summary_to_dict(s) for s in summaries],
        "total": total,
        "page_no": page_no,
        "page_size": page_size,
    }


@router.get("/agents/{agent_id}/llm-evals/runs/{run_id}")
def get_llm_eval_run_detail(
    agent_id: UUID,
    run_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """One run's summary + per-scenario scored rows. Org-scoped so a valid
    ``run_id`` from another tenant 404s."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmEvalService()
    detail = svc.get_run_detail(db, org_id=org_id, run_id=run_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found"
        )
    # Defensive: reject a run that belongs to a different agent in the same
    # org (the URL is agent-scoped, so silently returning it would be
    # misleading). Also caught by _ensure_agent_in_org above but that only
    # verifies the agent id, not that the run is FOR this agent.
    if detail["summary"].agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Eval run not found for this agent",
        )
    return {
        "summary": _run_summary_to_dict(detail["summary"]),
        "scenarios": detail["scenarios"],
    }


@router.post("/agents/{agent_id}/llm-evals/runs/compare")
def compare_llm_eval_runs(
    agent_id: UUID,
    body: CompareRunsRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Diff two runs of the same agent. Baseline / candidate summaries plus
    a per-scenario diff with per-metric deltas + regression flags — mirrors
    the RAG-eval compare shape so the FE reuses one component."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)

    # Cross-agent leak guard: the org filter alone lets a caller diff two
    # runs that belong to DIFFERENT agents in the same org (via a forged URL
    # that names agent A but supplies run_ids from agent B). Verify both
    # runs belong to the URL's agent BEFORE calling into the diff — otherwise
    # we'd render a nonsensical mixed-agent diff. Same 404 shape as
    # get_llm_eval_run_detail so callers can't distinguish "wrong agent"
    # from "no such run" without another API call.
    svc = AgentLlmEvalService()
    for label, run_id in (
        ("baseline", body.baseline_run_id),
        ("candidate", body.candidate_run_id),
    ):
        detail = svc.get_run_detail(db, org_id=org_id, run_id=run_id)
        if detail is None or detail["summary"].agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "RUN_NOT_FOUND",
                    "message": f"{label} run not found for this agent",
                },
            )
    try:
        return svc.compare_runs(
            db,
            org_id=org_id,
            baseline_run_id=body.baseline_run_id,
            candidate_run_id=body.candidate_run_id,
            score_drop=body.score_drop,
        )
    except EvalConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": str(e)},
        ) from e


# ── Folder routes ───────────────────────────────────────────────────────


@router.get("/agents/{agent_id}/llm-evals/folders")
def list_llm_eval_folders(
    agent_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Distinct folders for one agent plus each folder's scenario count.
    NULL folder is returned as ``{"folder": null, "count": N}`` so the UI
    can render "Uncategorized" without a second query."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    return {"items": svc.list_folders(agent_id)}


@router.post("/agents/{agent_id}/llm-evals/folders/rename")
def rename_llm_eval_folder(
    agent_id: UUID,
    body: RenameFolderRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Bulk-rename a folder for one agent. Updates BOTH
    ``agent_llm_eval_scenarios.folder`` AND ``agent_llm_eval_results.folder``
    in a single transaction so past runs regroup under the new name."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        return svc.rename_folder(
            agent_id, old_name=body.old_name, new_name=body.new_name
        )
    except (
        AgentLlmScenarioNotFoundError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e


@router.post("/agents/{agent_id}/llm-evals/folders/delete")
def delete_llm_eval_folder(
    agent_id: UUID,
    body: DeleteFolderRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Bulk-delete every scenario in a folder for one agent. Past run
    results keep their ``folder`` snapshot so the Runs tab history stays
    readable (matches the rename flow's history-preservation semantics).
    Returns ``{name, scenarios_deleted, results_preserved}`` so the FE
    confirmation toast can quote the exact numbers."""
    org_id = _resolve_org_id(claims)
    _ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentLlmScenarioService(db, org_id=org_id)
    try:
        return svc.delete_folder(agent_id, name=body.name)
    except (
        AgentLlmScenarioNotFoundError,
        AgentLlmEvalConfigError,
        EvalConfigurationError,
    ) as e:
        raise _handle_scenario_error(e) from e
