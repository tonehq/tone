"""Evaluation-config endpoints — reusable, org-wide judge recipes + re-grading.

Thin controllers: authenticate → resolve org → one service call → serialize.
All business logic lives in ``EvaluationConfigService``. Reads require an org
member; writes and the re-grade trigger require admin/owner (mirrors the
eval-settings guard).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import (
    JWTClaims,
    require_admin_or_owner,
    require_org_member,
)
from core.schemas.evaluation_config_requests import (
    EvaluationConfigCreateRequest,
    EvaluationConfigResultsListRequest,
    EvaluationConfigUpdateRequest,
    RunEvaluationConfigRequest,
)
from core.schemas.list_request import ListRequest
from core.services.evals.evaluation_config_service import EvaluationConfigService
from core.utils.org import resolve_org_id

router = APIRouter()


def _service(claims: JWTClaims, db: Session) -> EvaluationConfigService:
    return EvaluationConfigService(
        db, user_id=claims.user_id, org_id=resolve_org_id(claims)
    )


@router.post("/evaluation-configs", status_code=status.HTTP_201_CREATED)
def create_evaluation_config(
    body: EvaluationConfigCreateRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    config = _service(claims, db).create_config(**body.model_dump())
    return config.to_dict()


@router.put("/evaluation-configs/{config_id}")
def update_evaluation_config(
    config_id: str,
    body: EvaluationConfigUpdateRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    config = _service(claims, db).update_config(
        config_id, **body.model_dump(exclude_unset=True)
    )
    return config.to_dict()


@router.delete("/evaluation-configs/{config_id}", status_code=status.HTTP_200_OK)
def delete_evaluation_config(
    config_id: str,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    _service(claims, db).delete_config(config_id)
    return {"deleted": True}


@router.post("/evaluation-configs/{config_id}/set-default")
def set_default_evaluation_config(
    config_id: str,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    config = _service(claims, db).set_default(config_id)
    return config.to_dict()


@router.post("/evaluation-configs/list")
def list_evaluation_configs(
    body: ListRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    rows, total = _service(claims, db).list_configs(
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
        page_no=body.page,
        page_size=body.page_size,
    )
    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
    }


@router.post(
    "/evaluation-configs/run", status_code=status.HTTP_202_ACCEPTED
)
async def run_evaluation_config(
    body: RunEvaluationConfigRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Enqueue a background re-grade of a frozen eval run with one config.

    Validates the config and source run belong to the org (no cross-tenant
    grading) before deferring; the actual scoring runs on the ``eval`` queue.
    """
    # Local import — the worker enqueue helper pulls the Procrastinate app;
    # keep it off this router's module-load path.
    from core.services.evals.eval_service import EvalService
    from core.services.ingestion_queue import enqueue_evaluation_config_run

    org_id = resolve_org_id(claims)
    svc = _service(claims, db)
    svc.get_config(body.evaluation_config_id)  # 404 if not in this org

    rows = EvalService().get_scored_rows_for_run(
        db, run_id=body.source_run_id, org_id=org_id
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source run has no scored answers to re-judge.",
        )

    job_id = await enqueue_evaluation_config_run(
        source_run_id=body.source_run_id,
        evaluation_config_id=body.evaluation_config_id,
        triggered_by="manual",
    )
    return {"status": "queued", "job_id": job_id}


@router.post("/evaluation-config-results/list")
def list_evaluation_config_results(
    body: EvaluationConfigResultsListRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Config-result rows for a source run — the tab + compare read this.

    When ``config_run_ids`` is given (up to 3 for compare) results are limited
    to those passes; otherwise every pass against the source run is returned,
    plus a per-pass summary for the picker.
    """
    svc = _service(claims, db)
    return {
        "runs": svc.list_config_runs(source_run_id=body.source_run_id),
        "results": svc.list_results(
            source_run_id=body.source_run_id,
            config_run_ids=body.config_run_ids,
        ),
    }
