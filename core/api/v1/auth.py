from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Header
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.auth_service import AuthService
from core.middleware.auth import get_jwt_claims, JWTClaims, jwt_manager

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    email = user_data.get("email")
    password = user_data.get("password")
    username = user_data.get("username")
    profile = user_data.get("profile") or {}

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    return AuthService(db).signup(email, password, username, profile)


@router.post("/signup_with_firebase", status_code=status.HTTP_201_CREATED)
def signup_with_firebase(
    user_data: Dict[str, Any] = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
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

    return AuthService(db).signup_with_firebase(firebase_token, email, profile)


@router.get("/resend_verification_email")
def resend_verification_email(email: str = Query(...), db: Session = Depends(get_db)):
    return AuthService(db).resend_verification_email(email)


@router.get("/verify_user_email")
def verify_user_email(
    email: str = Query(...),
    code: str = Query(...),
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    return AuthService(db).verify_user_email(email, code, user_id)


@router.post("/login")
def login(login_data: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = login_data.get("email")
    password = login_data.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    return AuthService(db).login(email, password)


@router.get("/forget-password")
def forget_password(email: str = Query(...), db: Session = Depends(get_db)):
    return AuthService(db).forgot_password(email)


@router.get("/acceptForgotPassword")
def accept_forgot_password(
    email: str = Query(...),
    password: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    return AuthService(db).accept_forgot_password(email, password, token)
