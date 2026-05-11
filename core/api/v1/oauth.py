import time
import urllib.parse
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database.session import get_db
from core.services.oauth_service import OAuthService
from core.services.oauth_providers import get_provider_config, get_supported_providers
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()

# Backend base URL for the callback
BACKEND_URL = settings.BASE_API_URL.rstrip("/")  # e.g. http://localhost:8000/api/v1


def _get_service(claims: JWTClaims, db: Session) -> OAuthService:
    return OAuthService(db, org_id=UUID(claims.org_id) if claims.org_id else None)


# ─── CRUD endpoints ───


@router.get("/connections")
def get_connections(
    provider: str = Query(None, description="Filter by provider (e.g. google_calendar)"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connections = svc.get_connections(provider=provider, user_id=int(claims.user_id))
    return [svc.connection_response(c) for c in connections]


@router.get("/connection")
def get_connection_by_provider(
    provider: str = Query(..., description="Provider name (e.g. google_calendar)"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connection = svc.get_connection_by_provider(provider)
    if not connection:
        return {"connected": False, "provider": provider}
    return {**svc.connection_response(connection), "connected": True}


@router.delete("/disconnect", status_code=status.HTTP_200_OK)
def disconnect(
    connection_id: int = Query(..., description="The connection ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_connection(connection_id)


@router.get("/providers")
def list_providers():
    return {"providers": get_supported_providers()}


# ─── OAuth flow endpoints ───


@router.get("/{provider}/authorize")
def authorize(
    provider: str,
    claims: JWTClaims = Depends(require_org_member),
):
    """
    Step 1: Build the OAuth login URL and redirect the user to the provider's consent screen.
    """
    config = get_provider_config(provider)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    if not config["client_id"] or not config["client_secret"]:
        raise HTTPException(status_code=500, detail=f"OAuth credentials not configured for {provider}")

    # state carries org_id and user_id so the callback knows who initiated it
    state = f"{claims.org_id}:{claims.user_id}:{provider}"

    callback_url = f"{BACKEND_URL}/oauth/{provider}/callback"

    params = {
        "client_id": config["client_id"],
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": config["scopes"],
        "state": state,
        "access_type": "offline",  # needed to get refresh_token
        "prompt": "consent",  # force consent to always get refresh_token
    }

    auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/{provider}/callback")
def callback(
    provider: str,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter with org_id:user_id:provider"),
    db: Session = Depends(get_db),
):
    """
    Step 2: Provider redirects here with an auth code.
    Exchange the code for tokens and store them in the DB.
    """
    config = get_provider_config(provider)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    # Parse state to get org_id and user_id
    try:
        org_id_str, user_id_str, state_provider = state.split(":")
        org_id = UUID(org_id_str)
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    if state_provider != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch in state")

    callback_url = f"{BACKEND_URL}/oauth/{provider}/callback"

    # Exchange auth code for tokens
    token_data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": callback_url,
    }

    with httpx.Client() as client:
        response = client.post(config["token_url"], data=token_data)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {response.text}")

    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")  # seconds until expiry

    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received from provider")

    token_expiry = int(time.time()) + expires_in if expires_in else None

    # Get user email from Google's userinfo endpoint (for Google providers)
    user_email = None
    if provider.startswith("google"):
        try:
            with httpx.Client() as client:
                userinfo = client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if userinfo.status_code == 200:
                    user_email = userinfo.json().get("email")
        except Exception:
            pass

    # Store the connection
    svc = OAuthService(db, org_id=org_id)
    connection = svc.create_connection({
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": token_expiry,
        "scopes": config["scopes"],
        "user_email": user_email,
        "user_id": user_id,
    })

    # Redirect to frontend integrations page
    frontend_url = settings.APPLICATION_URL.rstrip("/")
    return RedirectResponse(url=f"{frontend_url}/integrations?provider={provider}&status=success")
