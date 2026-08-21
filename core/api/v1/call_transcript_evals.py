"""Post-call transcript eval read API — mounted in both editions from
``main.py``. The write path is entirely background (post-call action →
Procrastinate task → service persists the row) so there is no write endpoint
in v1; a future manual re-run endpoint fits alongside this file.

Router carries the full path (``/calls/{call_id}/eval-results``) so
``main.py`` mounts it without a prefix — same pattern as the agent-LLM
eval router.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.evals.call_transcript.service import (
    CallTranscriptEvalService,
)

router = APIRouter()


@router.get("/calls/{call_id}/eval-results")
def get_call_eval_results(
    call_id: UUID,
    db: Session = Depends(get_db),
    claims: JWTClaims = Depends(require_org_member),
) -> dict:
    """Return the DeepEval transcript-scoring result for one call.

    v1: at most one row per call (``mode='full_call'``). The response
    includes verdict + per-metric scores + judge reasoning + timing plus a
    ``reserved`` block (``tool_trace`` / ``rag_context`` / ``mcp_context`` —
    all ``null`` in v1) so the FE can render forward-compatible surfaces
    without a schema change when v2 wires those fields up.

    - 404 ``CALL_EVAL_NOT_FOUND`` when no row exists (cross-tenant reads
      also 404 — the service scopes by the caller's org via
      ``BaseService.query``, so a spoofed ``call_id`` returns ``None``).
    - 403 when the token is missing an ``org_id`` claim — without it, the
      service's ``BaseService.query`` would run unscoped and could leak
      another tenant's row.
    """
    # JWTClaims.org_id is Optional[str]; coerce to UUID (matches the
    # Procrastinate task's ``_UUID(org_id)`` before service construction).
    # A missing / malformed org claim is rejected here, NOT swallowed as a
    # 404, so we never fall through to an unscoped BaseService.query.
    if not claims.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MISSING_ORG_CLAIM",
                "message": "Token has no organization claim.",
            },
        )
    try:
        org_uuid = UUID(claims.org_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INVALID_ORG_CLAIM",
                "message": "Token organization claim is not a valid UUID.",
            },
        )

    svc = CallTranscriptEvalService(db, org_id=org_uuid)
    row = svc.get_result_for_call(call_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALL_EVAL_NOT_FOUND",
                "message": "No evaluation result exists for this call.",
            },
        )
    return row.to_dict()
