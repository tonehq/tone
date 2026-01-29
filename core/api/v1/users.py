from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.services.auth_service import AuthService
from core.middleware.auth import get_jwt_claims, require_org_member, JWTClaims

router = APIRouter()


@router.get("/get_all_users_for_organization")
def get_all_users_for_organization(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_all_users_for_organization()


@router.get("/get_all_invited_users_for_organization")
def get_all_invited_users_for_organization(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_all_invited_users_for_organization()
