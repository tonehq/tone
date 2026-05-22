from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from core.database.session import get_db
from ee.services.auth_service import EEAuthService
from ee.middleware.auth import get_ee_jwt_claims, require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.get("/me")
def get_me(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).get_user_me(claims.user_id)


@router.get("/get_all_users_for_organization")
def get_all_users_for_organization(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).get_all_users_for_organization(UUID(claims.org_id))


@router.get("/get_all_invited_users_for_organization")
def get_all_invited_users_for_organization(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).get_all_invited_users_for_organization(UUID(claims.org_id))
