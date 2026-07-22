from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.benchmark_service import MAX_CONCURRENCY, MAX_ITERATIONS, BenchmarkService
from shared.config import settings

router = APIRouter()


class BenchmarkRequest(BaseModel):
    config_id: Optional[str] = None
    service_types: Optional[List[str]] = None
    iterations: int = Field(default=5, ge=1, le=MAX_ITERATIONS)
    warmup_iterations: int = Field(default=1, ge=0, le=5)
    concurrency: int = Field(default=1, ge=1, le=MAX_CONCURRENCY)
    timeout_s: Optional[float] = Field(default=None, gt=0, le=120)
    measure: Literal["ttfb", "total"] = "ttfb"
    prompt: Optional[str] = None
    sentence: Optional[str] = None


def _get_service(claims: JWTClaims, db: Session) -> BenchmarkService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return BenchmarkService(db, user_id=user_id, org_id=org_id)


@router.get("/benchmark/types")
async def list_benchmark_types(
    _claims: JWTClaims = Depends(require_org_member),
) -> Dict[str, Any]:
    return {"service_types": BenchmarkService.available_types()}


@router.post("/{agent_id}/benchmark")
async def run_benchmark(
    agent_id: str,
    body: BenchmarkRequest = BenchmarkRequest(),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    svc = _get_service(claims, db)
    return await svc.run(
        agent_id,
        config_id=body.config_id,
        service_types=body.service_types,
        iterations=body.iterations,
        warmup_iterations=body.warmup_iterations,
        concurrency=body.concurrency,
        timeout_s=body.timeout_s,
        measure=body.measure,
        prompt=body.prompt,
        sentence=body.sentence,
    )
