from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.schemas.list_request import ListRequest, apply_list_request
from core.schemas.user import UserUpdate
from ee.services.auth_service import EEAuthService
from ee.middleware.auth import get_ee_jwt_claims, require_ee_org_member, EEJWTClaims

router = APIRouter()

MEMBER_SEARCH_FIELDS = ["first_name", "last_name", "username", "email"]
INVITE_SEARCH_FIELDS = ["name", "email", "role", "status"]


@router.get("/me")
def get_me(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).get_user_me(claims.user_id)


@router.patch("/me")
def update_me(
    payload: UserUpdate,
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).update_user_me(
        claims.user_id, payload.model_dump(exclude_unset=True)
    )


@router.post("/get_all_users_for_organization")
def get_all_users_for_organization(
    list_req: ListRequest = Body(default_factory=ListRequest),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    rows = EEAuthService(db, org_id=UUID(claims.org_id)).get_all_users_for_organization(
        UUID(claims.org_id)
    )
    return apply_list_request(rows, list_req, searchable_fields=MEMBER_SEARCH_FIELDS)


@router.post("/get_all_invited_users_for_organization")
def get_all_invited_users_for_organization(
    list_req: ListRequest = Body(default_factory=ListRequest),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    rows = EEAuthService(db, org_id=UUID(claims.org_id)).get_all_invited_users_for_organization(
        UUID(claims.org_id)
    )
    return apply_list_request(rows, list_req, searchable_fields=INVITE_SEARCH_FIELDS)
