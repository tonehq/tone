from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import get_jwt_claims, require_org_member, JWTClaims
from core.schemas.list_request import ListRequest, apply_list_request
from core.schemas.user import UserUpdate
from core.services.auth_service import AuthService

router = APIRouter()

MEMBER_SEARCH_FIELDS = ["first_name", "last_name", "username", "email"]
INVITE_SEARCH_FIELDS = ["name", "email", "role", "status"]


@router.get("/me")
def get_me(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    return AuthService(db).get_user_me(claims.user_id)


@router.patch("/me")
def update_me(
    payload: UserUpdate,
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    return AuthService(db).update_user_me(
        claims.user_id, payload.model_dump(exclude_unset=True)
    )


@router.post("/get_all_users_for_organization")
def get_all_users_for_organization(
    list_req: ListRequest = Body(default_factory=ListRequest),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    rows = AuthService(db).get_all_users_for_organization()
    return apply_list_request(rows, list_req, searchable_fields=MEMBER_SEARCH_FIELDS)


@router.post("/get_all_invited_users_for_organization")
def get_all_invited_users_for_organization(
    list_req: ListRequest = Body(default_factory=ListRequest),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    rows = AuthService(db).get_all_invited_users_for_organization()
    return apply_list_request(rows, list_req, searchable_fields=INVITE_SEARCH_FIELDS)
