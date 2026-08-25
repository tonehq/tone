import json
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.models.oauth_connection import OAuthConnection
from core.services.oauth_providers import (
    _row_by_slug,
    get_catalog,
    get_provider_config,
    get_supported_providers,
)
from core.services.oauth_service import OAuthService, normalize_scopes
from core.services.oauth_userinfo import fetch_user_email
from core.utils.auth_helpers import require_org_id
from core.utils.encryption import decrypt, decrypt_json, encrypt, encrypt_json
from core.utils.pkce import pkce_pair

# PKCE state lives in the encrypted ``state`` parameter for this long before the
# callback rejects it. Real-world OAuth handshakes complete in seconds; ten
# minutes is generous slack for slow consent screens or multi-factor prompts.
_PKCE_STATE_TTL_SECONDS = 600

router = APIRouter()

BACKEND_URL = settings.BASE_API_URL.rstrip("/")


def _get_service(claims: JWTClaims, db: Session) -> OAuthService:
    return OAuthService(db, org_id=require_org_id(claims.org_id))


# ─────────────────────────────────────────────────────────────────────
# Catalog-flow PKCE helpers. The actual verifier/challenge crypto lives
# in ``core.utils.pkce`` (shared with the MCP discovery flow).
# ─────────────────────────────────────────────────────────────────────


def _encode_pkce_state(
    verifier: str,
    org_id: UUID,
    user_id: UUID,
    provider_slug: str,
) -> str:
    """Encrypt the PKCE handshake context into an opaque OAuth ``state`` string.

    Carrying verifier + identity in the encrypted state lets the callback finish
    the handshake without an in-flight ``OAuthConnection`` row, which used to
    leak pending rows whenever a user abandoned the consent screen. Fernet's
    output is URL-safe base64, so it slots straight into a redirect URL.

    The payload also includes the originating ``provider_slug`` and an issued-at
    timestamp so the callback can reject state replayed for a different provider
    or after :data:`_PKCE_STATE_TTL_SECONDS`.
    """
    payload = json.dumps({
        "v": verifier,
        "o": str(org_id),
        "u": str(user_id),
        "p": provider_slug,
        "t": int(time.time()),
    })
    return encrypt(payload)


def _decode_pkce_state(state: str, provider: str) -> Optional[Dict[str, Any]]:
    """Inverse of :func:`_encode_pkce_state`. Returns ``None`` for any state
    that is not a current, valid PKCE token for this provider.

    Callers should fall through to :func:`_resolve_pkce_state` (legacy pending
    rows still in flight from before the stateless flow shipped) and finally to
    the ``org_id:user_id:provider`` legacy non-PKCE shape on a ``None`` here.
    """
    try:
        decoded = decrypt(state)
        payload = json.loads(decoded)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("p") != provider:
        return None
    if not payload.get("v"):
        return None
    issued = payload.get("t") or 0
    try:
        if int(time.time()) - int(issued) > _PKCE_STATE_TTL_SECONDS:
            return None
    except (TypeError, ValueError):
        return None
    return payload


def apply_resource_indicator(config: Dict[str, Any], token_data: Dict[str, Any]) -> None:
    resource = (config.get("extra_authorize_params") or {}).get("resource")
    if resource:
        token_data["resource"] = resource


def _resolve_pkce_state(
    db: Session, state: str, provider: str
) -> Tuple[Optional[OAuthConnection], Optional[str]]:
    """Resolve a UUID-shaped ``state`` to its pending row + verifier.

    Returns ``(pending_row, verifier)`` if found, ``(None, None)`` otherwise.
    Used only as a fallback for any pending rows that were inserted by the old
    PKCE flow before this code shipped — new handshakes use the stateless
    :func:`_encode_pkce_state` path and never write a pending row.
    """
    try:
        state_uuid = UUID(state)
    except (ValueError, TypeError):
        return None, None
    pending = (
        db.query(OAuthConnection)
        .filter(
            OAuthConnection.id == state_uuid,
            OAuthConnection.provider_slug == provider,
        )
        .first()
    )
    if not pending:
        return None, None
    creds = decrypt_json(pending.encrypted_credentials) or {}
    return pending, creds.get("code_verifier")


# ─── CRUD endpoints ───


@router.get("/connections")
def get_connections(
    provider: str = Query(None, description="Filter by provider (e.g. google_calendar)"),
    app_integration_id: str = Query(
        None,
        description="Filter to connections linked to this app_integrations row.",
    ),
    claims: JWTClaims = Depends(require_org_member),
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
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_connections(
        provider_slug=body.get("provider_slug"),
        app_integration_id=body.get("app_integration_id"),
    )


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


@router.post("/connections/{connection_id}/refresh")
def refresh_connection_token(
    connection_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """User-triggered refresh of a single OAuth connection's access token.

    Thin wrapper around ``OAuthService.get_valid_access_token_for_connection``
    — the SAME refresh path runtime + deep readiness use. Reused by three UI
    surfaces (Global Tools page, Global MCP page, agent readiness drawer) so
    a broken connection can be re-verified in-context without waiting for
    the next real call or running a full agent deep test.

    Success shape mirrors the connection-detail responses elsewhere in this
    router so callers can drop the payload into the same UI state.
    """
    svc = _get_service(claims, db)
    # ``get_connection`` is org-scoped via BaseService.query — a cross-org id
    # surfaces as 404, matching the semantics of every other endpoint here.
    connection = svc.get_connection(connection_id)
    # Provider-side failures (invalid_grant, invalid_client, network error)
    # raise HTTPException with a user-visible reason; let it bubble — the
    # OAuth router doesn't wrap OAuthService HTTPExceptions elsewhere either
    # (see /connection, /disconnect above). A follow-up refactor of
    # OAuthService to use application-level exceptions is out of scope.
    svc.get_valid_access_token_for_connection(connection)
    # Re-read to pick up the freshly-persisted token_expiry / rotated tokens.
    # ``update_tokens`` (inside ``get_valid_access_token_for_connection``) commits
    # + refreshes a *different* SQLAlchemy row, so the caller's ``connection``
    # object stays stale. A second fetch is the simplest way to get the fresh
    # public_metadata + tokens.
    #
    # Guard the re-read against a rare deletion race: another admin deleting
    # the same connection in the ~ms window between the refresh commit and
    # this fetch would otherwise turn a successful refresh into a confusing
    # 404. If that happens, fall back to reporting the refresh succeeded
    # without the freshly-persisted expiry — the DB already has the new
    # tokens even though we can't read them back through this session.
    try:
        refreshed = svc.get_connection(connection_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return {
                "status": "refreshed",
                "token_expiry": None,
                "connection": None,
            }
        raise
    return {
        "status": "refreshed",
        "token_expiry": (refreshed.public_metadata or {}).get("token_expiry"),
        "connection": svc.connection_response(refreshed),
    }


@router.delete("/disconnect", status_code=status.HTTP_200_OK)
def disconnect(
    connection_id: str = Query(..., description="The connection UUID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_connection(connection_id)


@router.get("/providers")
def list_providers(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return {"providers": get_supported_providers(db, org_id)}


@router.get("/catalog")
def catalog(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Public, secret-free provider catalog for the integrations grid."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return {"providers": get_catalog(db, org_id)}


@router.post("/custom_credential", status_code=status.HTTP_201_CREATED)
def create_custom_credential(
    body: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create a user-defined credential (OAuth 2.0 client-credentials, Bearer token, or API key).

    Body: { name, auth_kind: "oauth2_client_credentials" | "bearer" | "api_key",
            token_url?, client_id?, client_secret?, scope?, token?,
            api_key?, header_name? }
    """
    svc = _get_service(claims, db)
    connection = svc.create_custom_credential({**body, "created_by_user_id": claims.user_id})
    return svc.connection_response(connection)


# ─── Generic MCP OAuth 2.1 discovery (works with any compliant MCP server) ───

_MCP_CALLBACK_URL = f"{BACKEND_URL}/oauth/mcp/callback"


@router.post("/mcp/discover")
def mcp_discover(
    body: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Discover an MCP server's OAuth metadata, dynamically register a client, and return the
    authorization URL to redirect the user to. Body: { server_url, label?, return_to? }."""
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
        app_integration_id=body.get("app_integration_id"),
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
    from core.services.mcp_oauth_service import McpOAuthService

    # The pending connection row carries org scope; load it to resolve the org for the service.
    from core.models.oauth_connection import OAuthConnection

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
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    config = get_provider_config(db, org_id, provider)
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

    # PKCE branch: providers whose ``pkce_required`` is true (e.g. HubSpot's
    # MCP Auth App) need ``code_challenge`` + ``code_challenge_method``. We
    # carry the verifier + identity through the encrypted ``state`` parameter
    # so the callback can finish the handshake without inserting a row up
    # front — abandoned consent screens used to leave orphaned "pending"
    # connection rows in the DB. Non-PKCE providers keep the legacy
    # ``org:user:slug`` state format — backward compatible for everything
    # that worked before.
    if config.get("use_pkce"):
        user_uuid = UUID(str(claims.user_id))
        verifier, challenge = pkce_pair()
        params["state"] = _encode_pkce_state(verifier, org_id, user_uuid, provider)
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
    #      This is the only shape new authorize requests emit.
    #   2. UUID                    → legacy PKCE pending row (still in flight from
    #                                handshakes started before the stateless flow
    #                                shipped); the row carries verifier + identity.
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

    # Prefer the scopes the provider actually granted (returned in the token response) over the
    # ones we requested; fall back to the catalog's requested scopes when absent.
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
