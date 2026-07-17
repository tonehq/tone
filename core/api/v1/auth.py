from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import (
    JWTClaims,
    REFRESH_COOKIE,
    clear_auth_cookies,
    get_jwt_claims,
    get_optional_jwt_claims,
    set_cookies_and_strip,
)
from core.services.auth_service import AuthService
from core.utils.device import extract_device_context

router = APIRouter()


# ── Modern routes (preferred frontend surface) ─────────────────────────


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    request: Request,
    response: Response,
    user_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    email = user_data.get("email")
    password = user_data.get("password")
    profile = user_data.get("profile") or {}
    first_name = user_data.get("first_name") or profile.get("first_name")
    last_name = user_data.get("last_name") or profile.get("last_name")
    organization_name = (
        user_data.get("organization_name")
        or user_data.get("org_name")
        or profile.get("org_name")
    )

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )
    if not first_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="first_name is required",
        )

    result = AuthService(db).signup_v2(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name or "",
        organization_name=organization_name,
        device=extract_device_context(request),
    )
    return set_cookies_and_strip(response, result)


@router.post("/login")
def login(
    request: Request,
    response: Response,
    login_data: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
):
    email = login_data.get("email")
    password = login_data.get("password")
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )
    result = AuthService(db).login_v2(email, password, device=extract_device_context(request))
    return set_cookies_and_strip(response, result)


@router.post("/signin-code/request")
def request_signin_code(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="email is required"
        )
    return AuthService(db).request_signin_code(email)


@router.post("/signin-code/verify")
def verify_signin_code(
    request: Request,
    response: Response,
    body: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
):
    email = body.get("email")
    code = body.get("code")
    if not email or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email and code are required",
        )
    result = AuthService(db).verify_signin_code(
        email, code, device=extract_device_context(request),
    )
    return set_cookies_and_strip(response, result)


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    body: Dict[str, str] = Body(default={}),
    db: Session = Depends(get_db),
):
    # Prefer the httpOnly refresh cookie; fall back to a body token for
    # non-browser clients and the pre-cookie migration window.
    refresh_token = request.cookies.get(REFRESH_COOKIE) or (body or {}).get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )
    result = AuthService(db).refresh_tokens(refresh_token, device=extract_device_context(request))
    return set_cookies_and_strip(response, result)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE) or (body or {}).get("refresh_token")
    result = AuthService(db).logout(refresh_token=refresh_token)
    clear_auth_cookies(response)
    return result


@router.post("/verify-email")
def verify_email(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="token is required"
        )
    return AuthService(db).verify_email_by_token(token)


@router.post("/resend-verification")
def resend_verification(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="email is required"
        )
    return AuthService(db).resend_verification_email(email)


@router.post("/forgot-password")
def forgot_password(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="email is required"
        )
    return AuthService(db).request_password_reset(email)


@router.post("/reset-password")
def reset_password(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    token = body.get("token")
    new_password = body.get("new_password") or body.get("password")
    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token and new_password are required",
        )
    return AuthService(db).reset_password_by_token(token, new_password)


@router.post("/change-password")
def change_password(
    body: Dict[str, str] = Body(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    new_password = body.get("new_password")
    if not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="new_password is required"
        )
    return AuthService(db).change_password_for_user(claims.user_id, new_password)


@router.get("/me")
def get_me(claims: JWTClaims = Depends(get_jwt_claims), db: Session = Depends(get_db)):
    svc = AuthService(db)
    return {
        "user": svc.get_user_me(claims.user_id),
        "organization": svc.get_organization_me(claims.user_id),
    }


@router.get("/validate-invitation")
def validate_invitation(token: str = Query(...), db: Session = Depends(get_db)):
    return AuthService(db).validate_invitation_by_token(token)


@router.post("/accept-invitation")
def accept_invitation(
    request: Request,
    response: Response,
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    claims: Optional[JWTClaims] = Depends(get_optional_jwt_claims),
):
    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="token is required"
        )
    result = AuthService(db).accept_invitation_by_token(
        token=token,
        password=body.get("password"),
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        current_user_id=claims.user_id if claims else None,
        device=extract_device_context(request),
    )
    return set_cookies_and_strip(response, result)


# ── Legacy aliases (kept for older clients) ────────────────────────────


@router.get("/resend_verification_email")
def resend_verification_email_legacy(email: str = Query(...), db: Session = Depends(get_db)):
    return AuthService(db).resend_verification_email(email)


@router.get("/forget-password")
def forget_password_legacy(email: str = Query(...), db: Session = Depends(get_db)):
    return AuthService(db).forgot_password(email)
