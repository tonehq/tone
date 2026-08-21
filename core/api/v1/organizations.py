from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.auth_service import AuthService
from core.middleware.auth import get_jwt_claims, require_org_member, require_admin_or_owner, JWTClaims
from core.internal.capabilities import has_capability, is_ee_enabled
from core.internal.license import get_license_info
from core.models.member import Member
from core.context import get_current_org_id

router = APIRouter()

CORE_MAX_MEMBERS = 3


def require_team_capability():
    if not has_capability("t"):
        raise HTTPException(status_code=404, detail="Not found")


def check_member_limit(db: Session):
    if is_ee_enabled():
        license_info = get_license_info()
        if license_info.seats > 0:
            org_id = get_current_org_id()
            current_members = db.query(Member).filter(Member.organization_id == org_id).count()
            if current_members >= license_info.seats:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Member limit reached. Your license allows {license_info.seats} seats."
                )
    else:
        org_id = get_current_org_id()
        current_members = db.query(Member).filter(Member.organization_id == org_id).count()
        if current_members >= CORE_MAX_MEMBERS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Member limit reached. Core edition allows up to {CORE_MAX_MEMBERS} members. Upgrade to Enterprise for more."
            )


@router.get("/me")
def get_organization_me(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    return AuthService(db).get_organization_me(
        claims.user_id, org_id=get_current_org_id()
    )


@router.post("/invite_user_to_organization")
def invite_user_to_organization(
    invite_data: Dict[str, str] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    name = invite_data.get("name")
    email = invite_data.get("email")
    role = invite_data.get("role")

    if not all([name, email, role]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, email, and role are required"
        )

    check_member_limit(db)

    return AuthService(db, user_id=claims.user_id).invite_user_to_organization(name, email, role, claims.user_id)


@router.get("/accept_invitation")
def accept_invitation(
    email: str = Query(...),
    code: str = Query(...),
    db: Session = Depends(get_db)
):
    return AuthService(db).accept_invitation(email, code)


@router.get("/validate_invitation")
def validate_invitation(
    email: str = Query(...),
    code: str = Query(...),
    db: Session = Depends(get_db)
):
    return AuthService(db).validate_invitation_token(email, code)


@router.post("/accept_invitation_with_password")
def accept_invitation_with_password(
    payload: Dict[str, str] = Body(...),
    db: Session = Depends(get_db)
):
    email = payload.get("email")
    code = payload.get("code")
    password = payload.get("password")

    if not all([email, code, password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, code, and password are required"
        )

    return AuthService(db).accept_invitation_with_password(email, code, password)


@router.delete("/cancel_invitation")
def cancel_invitation(
    invite_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db, user_id=claims.user_id).cancel_invitation(invite_id)


@router.post("/resend_invitation")
def resend_invitation(
    invite_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return AuthService(db, user_id=claims.user_id).resend_invitation(invite_id)


@router.delete("/remove_user_from_organization")
def remove_user_from_organization(
    user_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db, user_id=claims.user_id).remove_user_from_organization(user_id)


@router.post("/update_member_role")
def update_member_role(
    member_id: int = Query(...),
    role: str = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db, user_id=claims.user_id).update_member_role(member_id, role)


@router.get("/settings")
def get_organization_settings(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_organization_settings()


@router.put("/settings")
def update_organization_settings(
    settings_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db).update_organization_settings(settings_data)


@router.get("/eval-settings")
def get_organization_eval_settings(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return the raw ``organizations.eval_settings`` JSONB for the current org.

    Unset keys are absent from the payload — the frontend renders those
    fields as placeholders showing the env/default that will actually be
    used. To see resolved values, run an eval and inspect the run row."""
    return AuthService(db).get_organization_eval_settings()


@router.put("/eval-settings")
def update_organization_eval_settings(
    patch: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Partial-update per-org eval settings (merged into the existing JSONB).

    Validation errors from the service surface as HTTP 400 with the exact
    per-field message so the UI can highlight the offending input. Missing
    org context (400) and unknown org id (404) come out of the service as
    typed exceptions — translated here per the transport-agnostic-service
    contract in ``.claude/skills/code-generator/backend-code-generator.md``.
    """
    # Local import — these exceptions live in the auth subtree; avoids
    # pulling them at module load time on every route mount.
    from core.services.auth_service import (
        OrganizationContextMissingError,
        OrganizationNotFoundError,
    )
    from core.services.evals.errors import InvalidEvalSettingsError

    try:
        return AuthService(db).update_organization_eval_settings(patch)
    except InvalidEvalSettingsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OrganizationContextMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/eval-settings/models")
def list_eval_settings_llm_models(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """LLM models offered as generation / answer model options on the
    Evaluations settings page. Filtered to OpenAI and Google (Gemini)
    providers — see ``EvalModelsService.list_llm_options`` for the exact
    contract and the reason for the allowlist."""
    # Local import — keeps this router's module load path unchanged for
    # every existing route and mirrors the pattern used for the eval
    # settings PUT below (see ``update_organization_eval_settings``).
    from core.services.evals.eval_models_service import EvalModelsService

    return EvalModelsService(db).list_llm_options()


@router.get("/access_requests")
def get_access_requests(
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_access_requests()


@router.post("/handle_access_request")
def handle_access_request(
    request_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    request_id = request_data.get("request_id")
    action = request_data.get("action")

    if not request_id or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request ID and action are required"
        )

    return AuthService(db, user_id=claims.user_id).handle_access_request(request_id, action, claims.user_id)


@router.get("/roles")
def get_roles(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_roles_by_scope()
