import time
import urllib.parse
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.api.v1.oauth import (
    _decode_pkce_state,
    _encode_pkce_state,
    _resolve_pkce_state,
    apply_resource_indicator,
)
from core.models.oauth_connection import OAuthConnection
from core.utils.pkce import pkce_pair
from core.config import settings
from core.database.session import get_db
from core.services.oauth_providers import (
    _row_by_slug,
    get_catalog,
    get_provider_config,
    get_supported_providers,
)
from core.services.oauth_service import OAuthService, normalize_scopes
from core.services.oauth_userinfo import fetch_user_email
from core.utils.auth_helpers import require_org_id
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()

BACKEND_URL = settings.BASE_API_URL.rstrip("/")


def _get_service(claims: EEJWTClaims, db: Session) -> OAuthService:
    return OAuthService(db, org_id=require_org_id(claims.org_id))


# ─── CRUD endpoints ───


@router.get("/connections")
def get_connections(
    provider: str = Query(None, description="Filter by provider (e.g. google_calendar)"),
    app_integration_id: str = Query(
        None,
        description="Filter to connections linked to this app_integrations row.",
    ),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connections = svc.get_connections(
        provider=provider,
        user_id=claims.user_id,
        app_integration_id=app_integration_id,
    )
    return [svc.connection_response(c) for c in connections]


@router.post("/list")
def list_connections(
    body: Dict[str, Any] = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_connections(
        provider_slug=body.get("provider_slug"),
        app_integration_id=body.get("app_integration_id"),
    )


@router.get("/connection")
def get_connection_by_provider(
    provider: str = Query(..., description="Provider name (e.g. google_calendar)"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connection = svc.get_connection_by_provider(provider)
    if not connection:
        return {"connected": False, "provider": provider}
    return {**svc.connection_response(connection), "connected": True}


@router.delete("/disconnect", status_code=status.HTTP_200_OK)
def disconnect(
    connection_id: str = Query(..., description="The connection UUID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_connection(connection_id)


@router.get("/providers")
def list_providers(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return {"providers": get_supported_providers(db, UUID(claims.org_id))}


@router.get("/catalog")
def catalog(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Public, secret-free provider catalog for the integrations grid."""
    return {"providers": get_catalog(db, UUID(claims.org_id))}


@router.post("/custom_credential", status_code=status.HTTP_201_CREATED)
def create_custom_credential(
    body: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Create a user-defined credential (OAuth 2.0 client-credentials or Bearer token)."""
    svc = _get_service(claims, db)
    connection = svc.create_custom_credential({**body, "created_by_user_id": claims.user_id})
    return svc.connection_response(connection)


# ─── Generic MCP OAuth 2.1 discovery (works with any compliant MCP server) ───

_MCP_CALLBACK_URL = f"{BACKEND_URL}/oauth/mcp/callback"


@router.post("/mcp/discover")
def mcp_discover(
    body: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Discover an MCP server's OAuth metadata, dynamically register a client, and return the
    authorization URL. Body: { server_url, label?, return_to? }."""
    from core.services.mcp_oauth_service import McpOAuthService

    server_url = body.get("server_url")
    if not server_url:
        raise HTTPException(status_code=400, detail="server_url is required")
    svc = McpOAuthService(
        db, org_id=require_org_id(claims.org_id), redirect_uri=_MCP_CALLBACK_URL
    )
    return svc.start_discovery(
        server_url=server_url,
        created_by_user_id=claims.user_id,
        label=body.get("label"),
        return_to=body.get("return_to"),
    )


def _mcp_callback_redirect(connection) -> RedirectResponse:
    """Send the user back to the in-app path that launched discovery (with the new connection id so
    the form can auto-select it), falling back to the integrations page."""
    frontend_url = settings.APPLICATION_URL.rstrip("/")
    return_to = (connection.public_metadata or {}).get("return_to")
    if return_to:
        sep = "&" if "?" in return_to else "?"
        target = f"{frontend_url}{return_to}{sep}mcp_oauth=success&connection_id={connection.id}"
    else:
        target = f"{frontend_url}/integrations?provider=mcp&status=success"
    return RedirectResponse(url=target)


@router.get("/mcp/callback")
def mcp_callback(
    code: str = Query(..., description="Authorization code from the MCP authorization server"),
    state: str = Query(..., description="The pending OAuth connection id"),
    db: Session = Depends(get_db),
):
    from core.models.oauth_connection import OAuthConnection
    from core.services.mcp_oauth_service import McpOAuthService

    connection = db.query(OAuthConnection).filter(OAuthConnection.id == state).first()
    if not connection:
        raise HTTPException(status_code=400, detail="Unknown or expired MCP OAuth state")

    svc = McpOAuthService(
        db, org_id=connection.organization_id, redirect_uri=_MCP_CALLBACK_URL
    )
    connection = svc.complete(connection_id=state, code=code)

    return _mcp_callback_redirect(connection)


# ─── OAuth flow endpoints ───


@router.get("/{provider}/authorize")
def authorize(
    provider: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    config = get_provider_config(db, UUID(claims.org_id), provider)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    if not config["client_id"] or not config["client_secret"]:
        raise HTTPException(
            status_code=500,
            detail=f"OAuth credentials not configured for {provider}",
        )

    callback_url = f"{BACKEND_URL}/oauth/{provider}/callback"
    params = {
        "client_id": config["client_id"],
        "redirect_uri": callback_url,
        "response_type": "code",
    }

    # PKCE branch — see ``core/api/v1/oauth.py`` for the design notes. The
    # verifier + identity ride through the encrypted ``state`` parameter so the
    # callback can finish the handshake without writing a pending row up front.
    if config.get("use_pkce"):
        org_uuid = UUID(claims.org_id)
        user_uuid = UUID(str(claims.user_id))
        verifier, challenge = pkce_pair()
        params["state"] = _encode_pkce_state(verifier, org_uuid, user_uuid, provider)
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"
    else:
        params["state"] = f"{claims.org_id}:{claims.user_id}:{provider}"

    # Some providers (Notion, ClickUp) have no OAuth scopes; omit the param entirely for them.
    scopes = config.get("scopes") or []
    if scopes:
        params["scope"] = config["scope_delimiter"].join(scopes)
    # Provider-specific extras (Google offline access, Notion owner=user, etc.).
    params.update(config.get("extra_authorize_params") or {})

    auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/{provider}/callback")
def callback(
    provider: str,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter with org_id:user_id:provider"),
    db: Session = Depends(get_db),
):
    # Three ``state`` shapes are accepted, in priority order:
    #   1. Fernet-encrypted JSON  → current PKCE flow; carries verifier + org + user.
    #      The only shape new authorize requests emit.
    #   2. UUID                    → legacy PKCE pending row (in-flight handshakes
    #                                from before the stateless flow shipped).
    #   3. ``org_id:user_id:provider`` → legacy non-PKCE flow.
    pending: Optional[OAuthConnection] = None
    verifier: Optional[str] = None
    encoded = _decode_pkce_state(state, provider)
    if encoded:
        org_id = UUID(encoded["o"])
        user_id = UUID(encoded["u"])
        verifier = encoded["v"]
    else:
        pending, verifier = _resolve_pkce_state(db, state, provider)
        if pending:
            org_id = pending.organization_id
            user_id = pending.created_by_user_id
        else:
            try:
                org_id_str, user_id_str, state_provider = state.split(":")
                org_id = UUID(org_id_str)
                user_id = UUID(user_id_str)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Invalid state parameter")
            if state_provider != provider:
                raise HTTPException(status_code=400, detail="Provider mismatch in state")

    config = get_provider_config(db, org_id, provider)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    callback_url = f"{BACKEND_URL}/oauth/{provider}/callback"

    token_data = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": callback_url,
    }
    # PKCE: include the verifier we stashed at authorize time. Providers that
    # didn't require PKCE just ignore the extra field.
    if verifier:
        token_data["code_verifier"] = verifier
    apply_resource_indicator(config, token_data)
    # Providers either accept client creds in the body (default) or require HTTP Basic (Notion).
    token_kwargs: Dict[str, Any] = {"data": token_data}
    if config.get("token_auth") == "basic":
        token_kwargs["auth"] = (config["client_id"], config["client_secret"])
    else:
        token_data["client_id"] = config["client_id"]
        token_data["client_secret"] = config["client_secret"]

    with httpx.Client() as client:
        response = client.post(config["token_url"], **token_kwargs)

    if response.status_code != 200:
        raise HTTPException(
            status_code=400, detail=f"Token exchange failed: {response.text}"
        )

    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")

    if not access_token:
        raise HTTPException(
            status_code=400, detail="No access token received from provider"
        )

    token_expiry = int(time.time()) + expires_in if expires_in else None

    # Prefer the scopes the provider actually granted; fall back to requested scopes.
    granted_scopes = normalize_scopes(tokens.get("scope")) or config["scopes"]

    user_email = fetch_user_email(provider, access_token, config.get("userinfo_url"))

    svc = OAuthService(db, org_id=org_id)
    token_payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": token_expiry,
        "scopes": granted_scopes,
        "user_email": user_email,
    }
    if pending:
        # Legacy PKCE pending row — promote it in place (or fold into an
        # existing duplicate). Routing through ``complete_pkce_connection``
        # avoids the duplicate-row bug ``create_connection``'s upsert hits
        # when the pending row lacks ``user_email``.
        connection = svc.complete_pkce_connection(
            pending=pending,
            token_data=token_payload,
            provider=provider,
            user_id=user_id,
            user_email=user_email,
        )
    else:
        # Stateless PKCE *and* non-PKCE both arrive here — no row exists yet,
        # so the upsert is the right tool (matches an existing row by
        # user_email when present, otherwise inserts a new one). Resolve the
        # catalog row up front so the new connection inherits its
        # ``app_integration_id`` for the per-integration filter in the picker.
        integration_row = _row_by_slug(db, org_id, provider)
        connection = svc.create_connection({
            "provider_slug": provider,
            "created_by_user_id": user_id,
            "app_integration_id": integration_row.id if integration_row else None,
            **token_payload,
        })

    frontend_url = settings.APPLICATION_URL.rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}/integrations?provider={provider}&status=success"
    )
