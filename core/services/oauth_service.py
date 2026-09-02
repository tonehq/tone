"""OAuth connection service — v2 schema.

Each connection lives in ``oauth_connections``:
  - ``provider_slug``   — e.g. ``google_calendar``
  - ``auth_type``       — ``oauth`` | ``api_key`` | ``bearer``
  - ``encrypted_credentials`` (JSONB) — opaque, encrypted access/refresh tokens
  - ``public_metadata`` (JSONB) — non-sensitive (user_email, scopes, token_expiry)
  - ``created_by_user_id`` (UUID) — who initiated the OAuth handshake
"""

import json
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from core.models.oauth_connection import OAuthConnection
from core.services.base import BaseService
from core.services.oauth_providers import (
    _row_by_slug,
    get_provider_config,
    get_provider_scopes,
)
from core.services.oauth_userinfo import fetch_user_email
from core.utils.auth_helpers import coerce_uuid
from core.utils.encryption import decrypt, decrypt_json, encrypt, encrypt_json
from core.utils.pkce import pkce_pair

# PKCE state lives in the encrypted ``state`` parameter for this long before the
# callback rejects it. Real-world OAuth handshakes complete in seconds; ten
# minutes is generous slack for slow consent screens or multi-factor prompts.
_PKCE_STATE_TTL_SECONDS = 600


def normalize_scopes(scopes: Any) -> List[str]:
    """Coerce a scope value into a clean list of strings.

    Accepts a list (returned as-is, de-duped, order-preserving), a delimited string
    (space- or comma-separated — the two delimiters OAuth providers use), or ``None``.
    Centralised so stored scopes are always a list regardless of provider quirks or legacy rows.
    """
    if not scopes:
        return []
    if isinstance(scopes, str):
        # Providers delimit scopes with either spaces (Google/Slack) or commas (Linear).
        parts = scopes.replace(",", " ").split()
    elif isinstance(scopes, (list, tuple, set)):
        parts = [str(s) for s in scopes]
    else:
        return []
    seen: set = set()
    result: List[str] = []
    for p in parts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ─────────────────────────────────────────────────────────────────────
# Catalog-flow PKCE state helpers. The actual verifier/challenge crypto lives
# in ``core.utils.pkce`` (shared with the MCP discovery flow). These state
# encode/decode/resolve helpers were moved verbatim out of the OAuth router so
# the flow lives in the service layer; the routers now delegate to
# ``OAuthService.build_authorize_url`` / ``OAuthService.exchange_code_and_persist``.
# ─────────────────────────────────────────────────────────────────────


def encode_pkce_state(
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


def decode_pkce_state(state: str, provider: str) -> Optional[Dict[str, Any]]:
    """Inverse of :func:`encode_pkce_state`. Returns ``None`` for any state
    that is not a current, valid PKCE token for this provider.

    Callers should fall through to :func:`resolve_pkce_state` (legacy pending
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


def resolve_pkce_state(
    db: Session, state: str, provider: str
) -> Tuple[Optional[OAuthConnection], Optional[str]]:
    """Resolve a UUID-shaped ``state`` to its pending row + verifier.

    Returns ``(pending_row, verifier)`` if found, ``(None, None)`` otherwise.
    Used only as a fallback for any pending rows that were inserted by the old
    PKCE flow before this code shipped — new handshakes use the stateless
    :func:`encode_pkce_state` path and never write a pending row.
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


# ─────────────────────────────────────────────────────────────────────
# Custom-credential builders (strategy registry keyed on ``auth_kind``).
# Each builder validates its inputs and returns ``(encrypted, metadata,
# auth_type)``; the shared ``create_custom_credential`` persists the resulting
# ``OAuthConnection``. ``service`` is passed so the client-credentials builder
# can mint a verification token via ``_request_client_credentials_token``.
# Adding a new credential kind = a new builder + one registry entry; the
# dispatch never changes. An unknown ``auth_kind`` raises the same 400 as before.
# ─────────────────────────────────────────────────────────────────────


def _build_bearer_credential(
    service: "OAuthService", data: Dict[str, Any], name: str
) -> Tuple[Any, Dict[str, Any], str]:
    token = (data.get("token") or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token is required for a bearer credential",
        )
    encrypted = encrypt_json({"access_token": token})
    metadata: Dict[str, Any] = {
        "credential_type": "custom",
        "auth_kind": "bearer",
        "status": "active",
    }
    return encrypted, metadata, "bearer"


def _build_api_key_credential(
    service: "OAuthService", data: Dict[str, Any], name: str
) -> Tuple[Any, Dict[str, Any], str]:
    # A raw API key applied to a caller-named header (default ``X-API-Key``).
    # Unlike bearer/oauth these never resolve to an ``Authorization: Bearer``
    # token — see ``resolve_connection_auth_header``.
    api_key = (data.get("api_key") or data.get("token") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key is required for an API key credential",
        )
    header_name = (data.get("header_name") or "X-API-Key").strip() or "X-API-Key"
    encrypted = encrypt_json({"api_key": api_key})
    metadata: Dict[str, Any] = {
        "credential_type": "custom",
        "auth_kind": "api_key",
        "header_name": header_name,
        "status": "active",
    }
    return encrypted, metadata, "api_key"


def _build_oauth2_client_credentials_credential(
    service: "OAuthService", data: Dict[str, Any], name: str
) -> Tuple[Any, Dict[str, Any], str]:
    token_url = (data.get("token_url") or "").strip()
    client_id = (data.get("client_id") or "").strip()
    client_secret = (data.get("client_secret") or "").strip()
    if not (token_url and client_id and client_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token_url, client_id and client_secret are required for OAuth 2.0",
        )
    scopes = normalize_scopes(data.get("scopes") or data.get("scope"))
    # Verify the credential up front by minting a real token, so a credential that can't
    # authenticate (e.g. a provider that doesn't support client-credentials) is rejected
    # here with a clear error instead of silently showing "Connected" then failing at use.
    token_result = service._request_client_credentials_token(
        token_url, client_id, client_secret, scopes, label=name
    )
    encrypted = encrypt_json(
        {"client_secret": client_secret, "access_token": token_result["access_token"]}
    )
    metadata: Dict[str, Any] = {
        "credential_type": "custom",
        "auth_kind": "oauth2_client_credentials",
        "grant_type": "client_credentials",
        "token_url": token_url,
        "client_id": client_id,
        "scopes": scopes,
        "token_expiry": int(time.time()) + int(token_result.get("expires_in", 3600)),
        "status": "active",
    }
    return encrypted, metadata, "oauth"


_CUSTOM_CREDENTIAL_BUILDERS = {
    "bearer": _build_bearer_credential,
    "api_key": _build_api_key_credential,
    "oauth2_client_credentials": _build_oauth2_client_credentials_credential,
}


class OAuthService(BaseService):
    # ──────────────────────────────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────────────────────────────

    def create_connection(self, data: Dict[str, Any]) -> OAuthConnection:
        """Persist a new OAuth connection from the provider callback payload.

        Expected keys: ``provider`` (alias: ``provider_slug``), ``access_token``,
        ``refresh_token``, ``token_expiry``, ``scopes``, ``user_email``,
        ``user_id`` (alias: ``created_by_user_id``), ``auth_type`` (default ``oauth``).
        """
        provider_slug = data.get("provider_slug") or data.get("provider")
        if not provider_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="provider_slug is required",
            )

        created_by = coerce_uuid(data.get("created_by_user_id") or data.get("user_id"))
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_by_user_id (UUID) is required",
            )

        user_email = data.get("user_email")
        existing_q = self.query(OAuthConnection).filter(
            OAuthConnection.provider_slug == provider_slug,
            OAuthConnection.created_by_user_id == created_by,
        )
        if user_email:
            existing_q = existing_q.filter(
                OAuthConnection.public_metadata["user_email"].astext == user_email
            )
        existing = existing_q.first()
        if existing:
            # Refresh the existing record in place instead of failing — the user
            # is reconnecting with the same identity.
            return self._apply_tokens(existing, data)

        public_metadata = {
            "user_email": user_email,
            "scopes": normalize_scopes(data.get("scopes")),
            "token_expiry": data.get("token_expiry"),
        }

        encrypted_credentials = encrypt_json({
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
        })

        connection = OAuthConnection(
            organization_id=self.org_id,
            provider_slug=provider_slug,
            label=data.get("label") or provider_slug.replace("_", " ").title(),
            auth_type=data.get("auth_type", "oauth"),
            encrypted_credentials=encrypted_credentials,
            public_metadata=public_metadata,
            created_by_user_id=created_by,
            app_integration_id=coerce_uuid(data.get("app_integration_id")),
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_connections(
        self,
        provider: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
        app_integration_id: Optional[Union[str, UUID]] = None,
    ) -> List[OAuthConnection]:
        """List connections in the current org, optionally filtered.

        ``app_integration_id`` lets the MCP / tool create forms show only
        connections that belong to the integration the user picked — e.g.
        only HubSpot connections when creating a HubSpot MCP.
        """
        q = self.query(OAuthConnection)
        if provider:
            q = q.filter(OAuthConnection.provider_slug == provider)
        uid = coerce_uuid(user_id)
        if uid is not None:
            q = q.filter(OAuthConnection.created_by_user_id == uid)
        aid = coerce_uuid(app_integration_id)
        if aid is not None:
            q = q.filter(OAuthConnection.app_integration_id == aid)
        return q.order_by(OAuthConnection.updated_at.desc()).all()

    def list_connections(
        self,
        provider_slug: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
        app_integration_id: Optional[Union[str, UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """Return every connection in the org (no pagination)."""
        q = self.query(OAuthConnection)
        if provider_slug:
            q = q.filter(OAuthConnection.provider_slug == provider_slug)
        uid = coerce_uuid(user_id)
        if uid is not None:
            q = q.filter(OAuthConnection.created_by_user_id == uid)
        aid = coerce_uuid(app_integration_id)
        if aid is not None:
            q = q.filter(OAuthConnection.app_integration_id == aid)
        items = q.order_by(OAuthConnection.updated_at.desc()).all()
        return [c.to_dict() for c in items]

    def list_connections_envelope(
        self,
        provider_slug: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
        app_integration_id: Optional[Union[str, UUID]] = None,
    ) -> Dict[str, Any]:
        """Wrap :meth:`list_connections` in the standard pagination envelope.

        The endpoint returns every connection in the org (no real pagination),
        so ``total`` == ``page_size`` == the number of items and ``page`` is 1.
        Centralised here so both the Core and EE ``POST /oauth/list`` routes
        emit an identical ``{items, total, page, page_size}`` shape.
        """
        items = self.list_connections(
            provider_slug=provider_slug,
            user_id=user_id,
            app_integration_id=app_integration_id,
        )
        total = len(items)
        return {"items": items, "total": total, "page": 1, "page_size": total}

    def get_connection_by_provider(self, provider: str) -> Optional[OAuthConnection]:
        return (
            self.query(OAuthConnection)
            .filter(OAuthConnection.provider_slug == provider)
            .order_by(OAuthConnection.updated_at.desc())
            .first()
        )

    def get_connection(self, connection_id: Union[str, UUID]) -> OAuthConnection:
        uid = coerce_uuid(connection_id)
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="connection_id must be a valid UUID",
            )
        connection = (
            self.query(OAuthConnection).filter(OAuthConnection.id == uid).first()
        )
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OAuth connection not found",
            )
        return connection

    def hydrate_summary_by_ids(
        self, connection_ids
    ) -> Dict[UUID, Dict[str, Any]]:
        """Return a ``{id: {id, token_expiry, provider_slug}}`` map for the
        given OAuth connection ids.

        Used by list endpoints (Tools, MCP) to attach a per-row OAuth status
        summary WITHOUT triggering N+1 lookups: one round-trip per list
        response regardless of row count. Only exposes the tiny public shape
        the UI needs — no access_token, no refresh_token, no encrypted
        credentials leak from this projection.

        Org-scoped automatically via ``BaseService.query`` — a cross-org id
        silently drops out of the map (matches ``get_connection`` semantics
        of returning 404 for the same case).
        """
        if not connection_ids:
            return {}
        # Deduplicate + coerce to UUIDs; skip anything not parseable so a
        # single bad id doesn't blow up the whole list response.
        #
        # A non-UUID id here is a data-integrity issue upstream (a Tool /
        # MCP row wrote a garbage ``oauth_connection_id``). Log so ops can
        # find the affected row instead of silently rendering "-" in the
        # OAuth column and letting the corruption stay invisible.
        parsed_ids: List[UUID] = []
        for cid in connection_ids:
            uid = coerce_uuid(cid)
            if uid is not None:
                parsed_ids.append(uid)
                continue
            logger.warning(
                "[oauth-hydrator] dropping non-UUID connection id (data-integrity issue upstream): {!r}",
                cid,
            )
        if not parsed_ids:
            return {}
        rows = (
            self.query(OAuthConnection)
            .filter(OAuthConnection.id.in_(set(parsed_ids)))
            .all()
        )
        return {
            row.id: {
                "id": str(row.id),
                "provider_slug": row.provider_slug,
                "token_expiry": (row.public_metadata or {}).get("token_expiry"),
            }
            for row in rows
        }

    def delete_connection(self, connection_id: Union[str, UUID]) -> Dict[str, str]:
        connection = self.get_connection(connection_id)
        # Disconnecting a connection leaves anything that relied on it unable to
        # authenticate. Deactivate those tools and MCP servers (and clear the
        # dangling link) so they aren't silently called and failing during a
        # conversation. The FK's SET NULL would otherwise leave them active but
        # unauthenticated, silently exposing zero tools at call time.
        from core.models.tool import Tool
        from core.models.mcp_server import McpServer

        self.db.query(Tool).filter(Tool.oauth_connection_id == connection.id).update(
            {Tool.is_active: False, Tool.oauth_connection_id: None},
            synchronize_session=False,
        )
        self.db.query(McpServer).filter(McpServer.oauth_connection_id == connection.id).update(
            {McpServer.is_active: False, McpServer.oauth_connection_id: None},
            synchronize_session=False,
        )
        self.db.delete(connection)
        self.db.commit()
        return {"message": "OAuth connection deleted successfully"}

    # ──────────────────────────────────────────────────────────────────────
    # Scope handling
    # ──────────────────────────────────────────────────────────────────────

    def get_granted_scopes(self, connection: OAuthConnection) -> List[str]:
        """Scopes actually granted to this connection (from ``public_metadata.scopes``)."""
        metadata = connection.public_metadata or {}
        return normalize_scopes(metadata.get("scopes"))

    def validate_scopes(
        self, connection: OAuthConnection, required: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Check whether ``connection`` was granted every scope in ``required``.

        Returns a structured result (never raises) so callers can choose to block or warn:
        ``{ ok, provider, granted: [...], required: [...], missing: [...] }``.
        """
        required_list = normalize_scopes(required)
        granted = set(self.get_granted_scopes(connection))
        missing = [s for s in required_list if s not in granted]
        return {
            "ok": len(missing) == 0,
            "provider": connection.provider_slug,
            "granted": sorted(granted),
            "required": required_list,
            "missing": missing,
        }

    def validate_connection_for_provider(
        self, connection: OAuthConnection, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate a connection against the catalog-declared scopes of ``provider``.

        Defaults to the connection's own provider when ``provider`` is omitted.
        """
        provider = provider or connection.provider_slug
        return self.validate_scopes(connection, get_provider_scopes(self.db, self.org_id, provider))

    @staticmethod
    def raise_if_missing_scopes(result: Dict[str, Any]) -> None:
        """Raise a 400 with the standard ``missing_scopes`` error contract when a scope
        validation result is not ``ok``. Single source of truth for the error shape so every
        config path (tool, MCP server, …) blocks with an identical, parseable response."""
        if result["ok"]:
            return
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    f"The linked '{result['provider']}' connection is missing required "
                    f"scopes. Reconnect it to grant: {', '.join(result['missing'])}."
                ),
                "code": "missing_scopes",
                "provider": result["provider"],
                "missing_scopes": result["missing"],
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # Custom credentials (Vapi-style)
    # ──────────────────────────────────────────────────────────────────────

    def create_custom_credential(self, data: Dict[str, Any]) -> OAuthConnection:
        """Create a user-defined credential not tied to a catalog provider.

        Supported ``auth_kind``:
          - ``oauth2_client_credentials`` — token_url + client_id + client_secret (+ scope);
            tokens are minted via the client-credentials grant on demand.
          - ``bearer`` — a static bearer token supplied directly.

        Stored as an ``OAuthConnection`` with ``provider_slug = "custom:<slug>"`` so it appears
        alongside other connections and can back a tool/MCP server via ``oauth_connection_id``.
        """
        import re

        created_by = coerce_uuid(data.get("created_by_user_id") or data.get("user_id"))
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_by_user_id (UUID) is required",
            )

        name = (data.get("name") or data.get("label") or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credential name is required",
            )

        auth_kind = data.get("auth_kind") or "oauth2_client_credentials"
        slug_suffix = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "credential"
        provider_slug = f"custom:{slug_suffix}"

        builder = _CUSTOM_CREDENTIAL_BUILDERS.get(auth_kind)
        if not builder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported auth_kind '{auth_kind}'",
            )
        encrypted, metadata, auth_type = builder(self, data, name)

        connection = OAuthConnection(
            organization_id=self.org_id,
            provider_slug=provider_slug,
            label=name,
            auth_type=auth_type,
            encrypted_credentials=encrypted,
            public_metadata=metadata,
            created_by_user_id=created_by,
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def _request_client_credentials_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: List[str],
        label: str = "credential",
    ) -> Dict[str, Any]:
        """Perform a client-credentials token request. Returns {access_token, expires_in}.

        Raises HTTPException(400) with a clear message on any failure so the caller (creation or
        refresh) surfaces it to the user rather than producing a half-working credential.
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scopes:
            payload["scope"] = " ".join(scopes)
        try:
            with httpx.Client() as client:
                response = client.post(token_url, data=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not reach the token URL for '{label}': {exc}",
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Client-credentials token request failed for '{label}' "
                    f"(HTTP {response.status_code}). This provider may not support the "
                    "client-credentials grant — check the token URL, client ID and secret."
                ),
            )
        body = response.json()
        access_token = body.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No access token returned for '{label}'.",
            )
        return {"access_token": access_token, "expires_in": body.get("expires_in", 3600)}

    def _mint_client_credentials_token(self, connection: OAuthConnection) -> str:
        """Return a cached client-credentials token, minting a fresh one when missing/expired."""
        metadata = connection.public_metadata or {}
        tokens = self.get_decrypted_tokens(connection)
        now = int(time.time())
        expiry = tokens.get("token_expiry")
        if tokens.get("access_token") and expiry and now < (expiry - 60):
            return tokens["access_token"]

        credentials = decrypt_json(connection.encrypted_credentials) or {}
        token_url = metadata.get("token_url")
        if not token_url:
            raise HTTPException(status_code=400, detail="Credential is missing a token URL.")

        result = self._request_client_credentials_token(
            token_url,
            metadata.get("client_id"),
            credentials.get("client_secret"),
            metadata.get("scopes") or [],
            label=connection.label or connection.provider_slug,
        )
        new_expiry = int(time.time()) + int(result.get("expires_in", 3600))
        self.update_tokens(connection.id, access_token=result["access_token"], token_expiry=new_expiry)
        return result["access_token"]

    # ──────────────────────────────────────────────────────────────────────
    # Token management
    # ──────────────────────────────────────────────────────────────────────

    def get_decrypted_tokens(self, connection: OAuthConnection) -> Dict[str, Any]:
        credentials = decrypt_json(connection.encrypted_credentials)
        metadata = connection.public_metadata or {}
        return {
            "access_token": credentials.get("access_token"),
            "refresh_token": credentials.get("refresh_token"),
            "token_expiry": metadata.get("token_expiry"),
        }

    def update_tokens(
        self,
        connection_id: Union[str, UUID],
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expiry: Optional[int] = None,
    ) -> OAuthConnection:
        connection = self.get_connection(connection_id)
        existing = decrypt_json(connection.encrypted_credentials)
        existing["access_token"] = access_token
        if refresh_token:
            existing["refresh_token"] = refresh_token
        connection.encrypted_credentials = encrypt_json(existing)
        metadata = dict(connection.public_metadata or {})
        if token_expiry:
            metadata["token_expiry"] = token_expiry
        connection.public_metadata = metadata
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_valid_access_token(self, provider: str) -> str:
        connection = self.get_connection_by_provider(provider)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active OAuth connection found for '{provider}'",
            )
        return self.get_valid_access_token_for_connection(connection)

    def resolve_connection_auth_header(
        self, connection: OAuthConnection
    ) -> Tuple[str, str]:
        """Resolve a connection into the ``(header_name, header_value)`` pair to
        apply on an outgoing request.

        API-key credentials carry a raw key applied to a caller-named header
        (``header_name`` in ``public_metadata``, default ``X-API-Key``) — they
        have no token flow, so they never route through
        ``get_valid_access_token_for_connection``. Every other kind (3-legged
        OAuth, static bearer, OAuth2 client-credentials) resolves to a fresh
        ``Authorization: Bearer <token>`` exactly as before.
        """
        metadata = connection.public_metadata or {}
        if metadata.get("auth_kind") == "api_key" or connection.auth_type == "api_key":
            tokens = self.get_decrypted_tokens(connection)
            api_key = tokens.get("api_key") or tokens.get("access_token")
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"API-key credential '{connection.label or connection.provider_slug}' "
                        "has no stored key."
                    ),
                )
            header_name = metadata.get("header_name") or "X-API-Key"
            return header_name, api_key
        token = self.get_valid_access_token_for_connection(connection)
        return "Authorization", f"Bearer {token}"

    async def resolve_connection_auth_header_async(
        self, connection: OAuthConnection
    ) -> Tuple[str, str]:
        """Async-safe wrapper around :meth:`resolve_connection_auth_header`.

        The sync method performs BLOCKING synchronous ``httpx.Client`` token
        requests (client-credentials mint / OAuth refresh), which would freeze
        the event loop if awaited on an async path (voice-pipeline tool
        handlers, ``mcp_server_service.upsert_mcp_server``). Async callers
        should ``await`` this wrapper, which runs the sync resolution in a
        worker thread. Semantics are identical for sync callers, who keep
        calling :meth:`resolve_connection_auth_header` directly.
        """
        return await run_in_threadpool(self.resolve_connection_auth_header, connection)

    def get_valid_access_token_for_connection(self, connection: OAuthConnection) -> str:
        provider = connection.provider_slug
        metadata = connection.public_metadata or {}

        # Custom credentials (Vapi-style) don't use the 3-legged authorization-code flow:
        #  - "bearer": a static token, returned as-is.
        #  - "oauth2_client_credentials": machine-to-machine grant, minted/cached on demand.
        auth_kind = metadata.get("auth_kind")
        if auth_kind == "bearer":
            token = self.get_decrypted_tokens(connection).get("access_token")
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bearer credential '{connection.label or provider}' has no token.",
                )
            return token
        if metadata.get("grant_type") == "client_credentials":
            return self._mint_client_credentials_token(connection)
        if auth_kind == "api_key" or connection.auth_type == "api_key":
            # API-key credentials have no token flow — without this guard they
            # fall into the refresh path below and fail with a misleading
            # "no refresh token" error.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Credential '{connection.label or provider}' is an API key and "
                    "cannot be resolved to a bearer token. Link an OAuth or bearer "
                    "credential instead."
                ),
            )

        try:
            tokens = self.get_decrypted_tokens(connection)
        except Exception as exc:
            # Decryption failed (rotated key, corrupted blob, etc.) — the user
            # needs to reconnect rather than see a generic 500.
            logger.exception(
                "Failed to decrypt stored credentials for provider '{}'; user must reconnect",
                provider,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stored credentials for '{provider}' could not be decrypted. Please reconnect.",
            ) from exc
        now = int(time.time())
        expiry = tokens.get("token_expiry")

        if expiry and now < (expiry - 60):
            return tokens["access_token"]

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token expired and no refresh token available for '{provider}'. Please reconnect.",
            )

        # Generic MCP connections (provider_slug ``mcp:<host>``) aren't in the catalog — their
        # token endpoint and dynamically-registered client live in the connection record itself.
        config = get_provider_config(self.db, self.org_id, provider)
        if config:
            token_url = config["token_url"]
            refresh_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        else:
            metadata = connection.public_metadata or {}
            token_url = metadata.get("token_endpoint")
            if not token_url:
                raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
            credentials = decrypt_json(connection.encrypted_credentials) or {}
            refresh_data = {
                "client_id": metadata.get("client_id"),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            if credentials.get("client_secret"):
                refresh_data["client_secret"] = credentials["client_secret"]
            if metadata.get("resource"):
                refresh_data["resource"] = metadata["resource"]

        with httpx.Client() as client:
            response = client.post(token_url, data=refresh_data)

        if response.status_code != 200:
            # Surface the provider's real reason (e.g. invalid_grant = token
            # expired/revoked → must reconnect; invalid_client = config issue).
            # Without this the failure is opaque and looks like a code bug.
            provider_error = ""
            try:
                body = response.json()
                provider_error = body.get("error") or ""
                if body.get("error_description"):
                    provider_error = f"{provider_error}: {body['error_description']}"
            except Exception:
                provider_error = (response.text or "")[:200]
            logger.warning(
                "OAuth refresh failed for '{}' (status={}): {}",
                provider, response.status_code, provider_error,
            )
            hint = "Please reconnect."
            if "invalid_grant" in provider_error:
                hint = (
                    "Refresh token expired or revoked — reconnect, and publish the "
                    "OAuth app (Google Cloud Console → OAuth consent screen) so tokens "
                    "stop expiring in 7 days."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token refresh failed for '{provider}' ({provider_error or response.status_code}). {hint}",
            )

        new_tokens = response.json()
        new_access_token = new_tokens["access_token"]
        new_expiry = int(time.time()) + new_tokens.get("expires_in", 3600)
        # Google may rotate refresh tokens; keep the old one if not returned.
        new_refresh_token = new_tokens.get("refresh_token")

        self.update_tokens(
            connection.id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_expiry=new_expiry,
        )
        return new_access_token

    async def get_valid_access_token_for_connection_async(
        self, connection: OAuthConnection
    ) -> str:
        """Async-safe wrapper around :meth:`get_valid_access_token_for_connection`.

        The sync method mints/refreshes tokens with a BLOCKING synchronous
        ``httpx.Client`` (client-credentials grant and the OAuth refresh POST),
        which freezes the event loop when awaited on an async path (voice
        pipeline tool handlers, ``custom_tool_service.handle_google_calendar``).
        Async callers should ``await`` this wrapper, which offloads the sync
        call to a worker thread. Sync callers are unaffected and keep calling
        the sync method directly.
        """
        return await run_in_threadpool(
            self.get_valid_access_token_for_connection, connection
        )

    # ──────────────────────────────────────────────────────────────────────
    # Response helpers
    # ──────────────────────────────────────────────────────────────────────

    def connection_response(self, connection: OAuthConnection) -> Dict[str, Any]:
        return connection.to_dict()

    # ──────────────────────────────────────────────────────────────────────
    # OAuth authorization-code flow (authorize URL + callback token exchange)
    #
    # These coarse entrypoints were moved verbatim out of the OAuth routers so
    # the business logic (provider config lookup, PKCE state, the token POST,
    # and the connection-persist branch) lives in the service layer. The routes
    # now only: parse request params → one call here → return the same response.
    # They take PLAIN args (no FastAPI Request/Depends) and resolve org scope
    # from the caller-supplied ``org_id`` / the ``state`` parameter, so both the
    # Core and EE routers share one implementation.
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def build_authorize_url(
        db: Session,
        provider: str,
        org_id: UUID,
        user_id: Any,
        backend_url: str,
    ) -> str:
        """Build the provider authorize URL (moved verbatim from the router).

        ``org_id`` is resolved by the caller (Core: with a ``DEFAULT_ORG_ID``
        fallback; EE: ``UUID(claims.org_id)``) so this preserves each edition's
        exact org-resolution. The emitted ``state`` is byte-for-byte the same:
        PKCE providers get the Fernet-encrypted state, everything else keeps the
        legacy ``org_id:user_id:provider`` shape.
        """
        config = get_provider_config(db, org_id, provider)
        if not config:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

        if not config["client_id"] or not config["client_secret"]:
            raise HTTPException(
                status_code=500,
                detail=f"OAuth credentials not configured for {provider}",
            )

        callback_url = f"{backend_url}/oauth/{provider}/callback"
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
            user_uuid = UUID(str(user_id))
            verifier, challenge = pkce_pair()
            params["state"] = encode_pkce_state(verifier, org_id, user_uuid, provider)
            params["code_challenge"] = challenge
            params["code_challenge_method"] = "S256"
        else:
            params["state"] = f"{org_id}:{user_id}:{provider}"

        # Some providers (Notion, ClickUp) have no OAuth scopes; omit the param entirely for them.
        scopes = config.get("scopes") or []
        if scopes:
            params["scope"] = config["scope_delimiter"].join(scopes)
        # Provider-specific extras (Google offline access, Notion owner=user, etc.).
        params.update(config.get("extra_authorize_params") or {})

        return f"{config['auth_url']}?{urllib.parse.urlencode(params)}"

    @classmethod
    def exchange_code_and_persist(
        cls,
        db: Session,
        provider: str,
        code: str,
        state: str,
        backend_url: str,
    ) -> OAuthConnection:
        """Resolve the ``state``, exchange the code for tokens, and persist the
        connection (moved verbatim from the router callback).

        Three ``state`` shapes are accepted, in priority order:
          1. Fernet-encrypted JSON  → current PKCE flow; carries verifier + org + user.
             This is the only shape new authorize requests emit.
          2. UUID                    → legacy PKCE pending row (still in flight from
                                       handshakes started before the stateless flow
                                       shipped); the row carries verifier + identity.
          3. ``org_id:user_id:provider`` → legacy non-PKCE flow.

        The org scope is derived from ``state`` (not the caller), so the persist
        step builds an org-scoped service ``cls(db, org_id=org_id)`` exactly as
        the router did. Returns the persisted connection; the caller renders the
        same browser redirect.
        """
        pending: Optional[OAuthConnection] = None
        verifier: Optional[str] = None
        encoded = decode_pkce_state(state, provider)
        if encoded:
            org_id = UUID(encoded["o"])
            user_id = UUID(encoded["u"])
            verifier = encoded["v"]
        else:
            pending, verifier = resolve_pkce_state(db, state, provider)
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

        callback_url = f"{backend_url}/oauth/{provider}/callback"

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

        svc = cls(db, org_id=org_id)
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
        return connection

    def complete_pkce_connection(
        self,
        pending: OAuthConnection,
        token_data: Dict[str, Any],
        provider: str,
        user_id,
        user_email: Optional[str],
    ) -> OAuthConnection:
        """Finalise a PKCE catalog OAuth handshake without creating duplicates.

        At authorize time the PKCE flow creates a ``pending`` row to park the
        verifier + ``app_integration_id``. That row has no ``user_email`` yet,
        so :meth:`create_connection`'s ``(provider_slug, user_id, user_email)``
        upsert filter can't find it — calling ``create_connection`` here would
        therefore insert a *second* row and orphan the pending one (the bug
        this method exists to prevent).

        Resolution order:

        1. If a pre-existing active row matches the same provider + user +
           ``user_email``, the user is reconnecting. Update *that* row,
           inherit ``app_integration_id`` from the pending row if it's
           missing, and drop the pending scratchpad.
        2. Otherwise the pending row IS the canonical connection — apply
           tokens to it in place and clear the ``status="pending"`` marker.
        """
        duplicate: Optional[OAuthConnection] = None
        if user_email:
            duplicate = (
                self.query(OAuthConnection)
                .filter(
                    OAuthConnection.provider_slug == provider,
                    OAuthConnection.created_by_user_id == user_id,
                    OAuthConnection.id != pending.id,
                    OAuthConnection.public_metadata["user_email"].astext == user_email,
                )
                .first()
            )

        if duplicate:
            if not duplicate.app_integration_id and pending.app_integration_id:
                duplicate.app_integration_id = pending.app_integration_id
            connection = self._apply_tokens(duplicate, token_data)
            self.db.delete(pending)
            self.db.commit()
            return connection

        connection = self._apply_tokens(pending, token_data)
        return self.clear_pending_status(connection)

    def clear_pending_status(self, connection: OAuthConnection) -> OAuthConnection:
        """Drop the ``status='pending'`` marker from a connection's metadata.

        The PKCE catalog flow stamps ``public_metadata.status = 'pending'`` at
        authorize time so the partially-populated row is filtered out of the
        connection picker. After the callback completes the token exchange,
        :meth:`_apply_tokens` (called via :meth:`create_connection`) merges
        new fields into metadata but never removes the marker — so callers
        must explicitly clear it here once the row is fully populated.

        Idempotent: rows that don't have a pending marker are returned
        unchanged with no DB write.
        """
        metadata = connection.public_metadata or {}
        if metadata.get("status") != "pending":
            return connection
        updated = dict(metadata)
        updated.pop("status", None)
        connection.public_metadata = updated
        self.db.commit()
        return connection

    # ──────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────

    def _apply_tokens(self, connection: OAuthConnection, data: Dict[str, Any]) -> OAuthConnection:
        credentials = decrypt_json(connection.encrypted_credentials)
        credentials["access_token"] = data["access_token"]
        if data.get("refresh_token"):
            credentials["refresh_token"] = data["refresh_token"]
        connection.encrypted_credentials = encrypt_json(credentials)

        metadata = dict(connection.public_metadata or {})
        if data.get("token_expiry") is not None:
            metadata["token_expiry"] = data["token_expiry"]
        if data.get("scopes") is not None:
            metadata["scopes"] = normalize_scopes(data["scopes"])
        if data.get("user_email") is not None:
            metadata["user_email"] = data["user_email"]
        connection.public_metadata = metadata

        self.db.commit()
        self.db.refresh(connection)
        return connection
