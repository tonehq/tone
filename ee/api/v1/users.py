from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from ee.database.session import get_ee_db
from ee.services.auth_service import EEAuthService
from ee.middleware.auth import get_ee_current_user, require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.get("/get_all_users_for_organization")
def get_all_users_for_organization(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).get_all_users_for_organization(UUID(claims.org_id))


@router.get("/get_all_invited_users_for_organization")
def get_all_invited_users_for_organization(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).get_all_invited_users_for_organization(UUID(claims.org_id))
