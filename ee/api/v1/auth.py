from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Header
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from ee.database.session import get_ee_db
from ee.services.auth_service import EEAuthService
from ee.middleware.auth import get_ee_jwt_claims, EEJWTClaims

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_data: Dict[str, Any] = Body(...), db: Session = Depends(get_ee_db)):
    email = user_data.get("email")
    password = user_data.get("password")
    username = user_data.get("username")
    profile = user_data.get("profile") or {}
    org_name = user_data.get("org_name")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    return EEAuthService(db).signup(email, password, username, profile, org_name)


@router.get("/check_organization_exists")
def check_organization_exists(name: str = Query(...), db: Session = Depends(get_ee_db)):
    return EEAuthService(db).check_organization_exists(name)


@router.post("/signup_with_firebase", status_code=status.HTTP_201_CREATED)
def signup_with_firebase(
    user_data: Dict[str, Any] = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_ee_db)
):
    email = user_data.get("email")
    profile = user_data.get("profile")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )

    firebase_token = authorization.split("Bearer ")[1]

    return EEAuthService(db).signup_with_firebase(firebase_token, email, profile)


@router.get("/resend_verification_email")
def resend_verification_email(email: str = Query(...), db: Session = Depends(get_ee_db)):
    return EEAuthService(db).resend_verification_email(email)


@router.get("/verify_user_email")
def verify_user_email(
    email: str = Query(...),
    code: str = Query(...),
    user_id: int = Query(...),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db).verify_user_email(email, code, user_id)


@router.post("/login")
def login(login_data: Dict[str, str] = Body(...), db: Session = Depends(get_ee_db)):
    email = login_data.get("email")
    password = login_data.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    return EEAuthService(db).login(email, password)


@router.get("/forget-password")
def forget_password(email: str = Query(...), db: Session = Depends(get_ee_db)):
    return EEAuthService(db).forgot_password(email)


@router.get("/acceptForgotPassword")
def accept_forgot_password(
    email: str = Query(...),
    password: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db).accept_forgot_password(email, password, token)


@router.post("/switch_organization")
def switch_organization(
    org_data: Dict[str, str] = Body(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_ee_db)
):
    org_id = org_data.get("organization_id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )

    return EEAuthService(db).switch_organization(claims.user_id, UUID(org_id))
