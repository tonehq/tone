from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import (APIRouter, Body, Depends, Header, HTTPException, Query,
                     Request, status)
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.utils.device import extract_device_context
from ee.middleware.auth import (
    EEJWTClaims,
    get_ee_jwt_claims,
    get_optional_ee_jwt_claims,
)
from ee.services.auth_service import EEAuthService

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    request: Request,
    user_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    email = user_data.get("email")
    password = user_data.get("password")
    first_name = user_data.get("first_name") or (user_data.get("profile") or {}).get("first_name")
    last_name = user_data.get("last_name") or (user_data.get("profile") or {}).get("last_name")
    organization_name = user_data.get("organization_name") or user_data.get("org_name")
    username = user_data.get("username")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    device = extract_device_context(request)

    # Prefer the v2 shape when first/last name are supplied (new auth UI).
    if first_name and last_name:
        return EEAuthService(db).signup_v2(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            organization_name=organization_name,
            device=device,
        )

    profile = user_data.get("profile") or {}
    return EEAuthService(db).signup(email, password, username or None, profile, organization_name)


@router.get("/check_organization_exists")
def check_organization_exists(name: str = Query(...), db: Session = Depends(get_db)):
    return EEAuthService(db).check_organization_exists(name)


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

    return EEAuthService(db).signup_with_firebase(firebase_token, email, profile)


@router.get("/resend_verification_email")
def resend_verification_email(email: str = Query(...), db: Session = Depends(get_db)):
    return EEAuthService(db).resend_verification_email(email)


@router.get("/verify_user_email")
def verify_user_email(
    email: str = Query(...),
    code: str = Query(...),
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    return EEAuthService(db).verify_user_email(email, code, user_id)


@router.post("/login")
def login(
    request: Request,
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

    return EEAuthService(db).login_v2(email, password, device=extract_device_context(request))


@router.post("/refresh")
def refresh(
    request: Request,
    body: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
):
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )
    return EEAuthService(db).refresh_tokens(refresh_token, device=extract_device_context(request))


@router.post("/logout")
def logout(body: Dict[str, Any] = Body(default={}), db: Session = Depends(get_db)):
    return EEAuthService(db).logout(refresh_token=body.get("refresh_token"))


@router.post("/verify-email")
def verify_email(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="token is required"
        )
    return EEAuthService(db).verify_email_by_token(token)


@router.post("/resend-verification")
def resend_verification(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="email is required"
        )
    return EEAuthService(db).resend_verification_email(email)


@router.post("/forgot-password")
def forgot_password(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="email is required"
        )
    return EEAuthService(db).request_password_reset(email)


@router.post("/reset-password")
def reset_password(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    token = body.get("token")
    new_password = body.get("new_password") or body.get("password")
    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token and new_password are required",
        )
    return EEAuthService(db).reset_password_by_token(token, new_password)


@router.post("/change-password")
def change_password(
    body: Dict[str, str] = Body(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    new_password = body.get("new_password")
    if not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="new_password is required"
        )
    return EEAuthService(db).change_password_for_user(claims.user_id, new_password)


@router.get("/validate-invitation")
def validate_invitation(token: str = Query(...), db: Session = Depends(get_db)):
    return EEAuthService(db).validate_invitation_by_token(token)


@router.post("/accept-invitation")
def accept_invitation(
    request: Request,
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    claims: Optional[EEJWTClaims] = Depends(get_optional_ee_jwt_claims),
):
    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="token is required"
        )
    return EEAuthService(db).accept_invitation_by_token(
        token=token,
        password=body.get("password"),
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        current_user_id=claims.user_id if claims else None,
        device=extract_device_context(request),
    )


@router.get("/forget-password")
def forget_password(email: str = Query(...), db: Session = Depends(get_db)):
    return EEAuthService(db).forgot_password(email)


@router.get("/acceptForgotPassword")
def accept_forgot_password(
    email: str = Query(...),
    password: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    return EEAuthService(db).accept_forgot_password(email, password, token)


@router.post("/switch_organization")
def switch_organization(
    org_data: Dict[str, str] = Body(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db)
):
    org_id = org_data.get("organization_id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )

    return EEAuthService(db).switch_organization(claims.user_id, UUID(org_id))
