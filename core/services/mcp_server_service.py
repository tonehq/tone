import base64
from urllib.parse import urlparse
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from starlette.concurrency import run_in_threadpool

from sqlalchemy import case, or_

from core.services.agent_attachment_sync import get_attached_agents, sync_agent_attachments
from core.services.audit_actions import AgentAuditAction, AuditResourceType
from core.services.base import BaseService
from core.models.mcp_server import McpServer
from core.models.agent_mcp_server import AgentMcpServer
from core.models.tool import Tool
from core.utils.auth_types import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_BASIC,
    AUTH_TYPE_BEARER,
    AUTH_TYPE_NONE,
    AUTH_TYPE_OAUTH,
    VALID_AUTH_TYPES,
    normalize_auth_type,
)
from core.utils.encryption import encrypt, decrypt
from core.utils.faceted_query import apply_filters, apply_sort, build_facets, distinct_values


def encrypt_auth_config(auth_config):
    if not auth_config:
        return auth_config
    encrypted = {}
    for key, value in auth_config.items():
        if isinstance(value, str) and value:
            encrypted[key] = encrypt(value)
        elif key == "headers" and isinstance(value, list):
            encrypted[key] = [
                {k: encrypt(v) if isinstance(v, str) and v else v for k, v in h.items()}
                for h in value
            ]
        else:
            encrypted[key] = value
    return encrypted


def decrypt_auth_config(auth_config):
    if not auth_config:
        return auth_config
    decrypted = {}
    for key, value in auth_config.items():
        if isinstance(value, str) and value:
            try:
                decrypted[key] = decrypt(value)
            except Exception:
                decrypted[key] = value
        elif key == "headers" and isinstance(value, list):
            decrypted[key] = [
                {k: _try_decrypt(v) if isinstance(v, str) and v else v for k, v in h.items()}
                for h in value
            ]
        else:
            decrypted[key] = value
    return decrypted


def _try_decrypt(value):
    try:
        return decrypt(value)
    except Exception:
        return value


def build_auth_headers(
    auth_config,
    already_decrypted: bool = False,
    auth_type: Optional[str] = None,
) -> dict:
    """Build HTTP headers from ``auth_config`` for an MCP server.

    When ``auth_type`` is provided, the header shape is chosen explicitly:

    * ``'bearer'`` -> ``Authorization: Bearer <bearer_token>``
    * ``'api_key'`` -> ``<auth_header or 'Authorization'>: <scheme> <api_key>``
      (scheme defaults to ``'Bearer'``; pass ``auth_scheme=''`` for a raw token)
    * ``'basic'`` -> ``Authorization: Basic <base64(username:password)>``
    * ``'oauth'`` / ``'none'`` -> no header from ``auth_config`` (OAuth headers
      come from the connection resolver at call time)

    When ``auth_type`` is ``None`` (legacy rows written before the column existed),
    fall back to merging every source found in ``auth_config``. Explicit custom
    headers still win on name conflicts. This preserves the pre-``auth_type``
    behavior for any row that hasn't been migrated / re-saved yet.
    """
    if not auth_config:
        return {}
    decrypted = auth_config if already_decrypted else decrypt_auth_config(auth_config)
    headers: dict = {}

    _apply_custom_headers(decrypted, headers)

    normalized = normalize_auth_type(auth_type) if auth_type is not None else None
    if normalized is None:
        _apply_legacy_auth_config(decrypted, headers)
        return headers

    if normalized == AUTH_TYPE_BEARER:
        token = decrypted.get("bearer_token") or decrypted.get("token")
        if token:
            headers.setdefault("Authorization", f"Bearer {token}")
    elif normalized == AUTH_TYPE_API_KEY:
        api_key = decrypted.get("api_key")
        if api_key:
            target = (
                decrypted.get("auth_header")
                or decrypted.get("api_key_header")
                or "Authorization"
            )
            scheme = decrypted.get("auth_scheme")
            if scheme is None:
                scheme = "Bearer"
            value = f"{scheme} {api_key}".strip() if scheme else str(api_key)
            if not any(k.lower() == target.lower() for k in headers):
                headers[target] = value
    elif normalized == AUTH_TYPE_BASIC:
        username = decrypted.get("username", "")
        password = decrypted.get("password", "")
        if username or password:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers.setdefault("Authorization", f"Basic {credentials}")
    # AUTH_TYPE_OAUTH / AUTH_TYPE_NONE: no auth_config-sourced header.

    return headers


def _apply_custom_headers(decrypted: dict, headers: dict) -> None:
    """Merge custom ``x-*`` headers (both list-form and legacy pair-form) into
    ``headers``. Shared across every auth_type since a server can carry custom
    headers (e.g. ClickUp's ``x-workspace-id``) alongside its auth."""
    if isinstance(decrypted.get("headers"), list):
        for h in decrypted["headers"]:
            if h.get("header_name") and h.get("header_value"):
                headers[h["header_name"]] = h["header_value"]

    if decrypted.get("header_name") and decrypted.get("header_value"):
        headers.setdefault(decrypted["header_name"], decrypted["header_value"])


def _apply_legacy_auth_config(decrypted: dict, headers: dict) -> None:
    """Legacy behavior: infer bearer/api_key from the JSON keys.

    Only used for rows written before the ``auth_type`` column existed. Once a
    row is saved with ``auth_type`` set, the explicit branches in
    :func:`build_auth_headers` handle it and this fallback is skipped.
    """
    secret = decrypted.get("api_key") or decrypted.get("token") or decrypted.get("bearer_token")
    if not secret:
        return
    target = decrypted.get("auth_header") or decrypted.get("api_key_header") or "Authorization"
    scheme = decrypted.get("auth_scheme")
    if scheme is None:
        scheme = "Bearer"
    value = f"{scheme} {secret}".strip() if scheme else str(secret)
    if not any(k.lower() == target.lower() for k in headers):
        headers[target] = value


SECRET_URL_KEY = "server_url"
_MASKED_URL = "********"


def effective_server_url(auth_config, fallback: str) -> str:
    return (auth_config or {}).get(SECRET_URL_KEY) or fallback


def resolve_server_url(mcp_server) -> str:
    decrypted = decrypt_auth_config(mcp_server.auth_config) or {}
    return decrypted.get(SECRET_URL_KEY) or mcp_server.server_url


def has_secret_url(auth_config) -> bool:
    return bool((auth_config or {}).get(SECRET_URL_KEY))


def public_url_for(secret_url: str) -> str:
    parsed = urlparse(secret_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    first = next((seg for seg in parsed.path.split("/") if seg), None)
    return f"{origin}/{first}" if first else origin


def strip_masked_secret_url(incoming, existing_auth_config):
    if not incoming or incoming.get(SECRET_URL_KEY) != _MASKED_URL:
        return incoming
    result = dict(incoming)
    previous = (decrypt_auth_config(existing_auth_config) or {}).get(SECRET_URL_KEY)
    if previous:
        result[SECRET_URL_KEY] = previous
    else:
        result.pop(SECRET_URL_KEY, None)
    return result


def mask_auth_config_url(auth_config) -> dict:
    if not auth_config:
        return auth_config
    if SECRET_URL_KEY not in auth_config:
        return auth_config
    return {**auth_config, SECRET_URL_KEY: _MASKED_URL}


def _masked_auth_config(auth_config):
    """Return an auth_config with the same KEYS/structure but every secret VALUE
    replaced by the fixed ``_MASKED_URL`` sentinel, WITHOUT decrypting anything.

    Used for broad/list responses so credentials (``api_key``, ``bearer_token``,
    the ``server_url``, and any custom header values) are never dumped in
    plaintext. Only the single-item edit-fetch (``get_mcp_server``) passes
    ``mask_secrets=False`` to return the real decrypted config the edit form
    needs to pre-fill.

    Structure is preserved: the nested ``headers`` list keeps its shape with each
    string value masked, and non-string / structural values pass through
    untouched. ``server_url`` collapses to the same sentinel
    :func:`mask_auth_config_url` already emits. ``None``/falsy stays ``None``.
    """
    if not auth_config:
        return None
    masked = {}
    for key, value in auth_config.items():
        if key == "headers" and isinstance(value, list):
            masked[key] = [
                {k: (_MASKED_URL if isinstance(v, str) and v else v) for k, v in h.items()}
                for h in value
            ]
        elif isinstance(value, str) and value:
            masked[key] = _MASKED_URL
        else:
            masked[key] = value
    return masked


def headers_from_meta(meta_data) -> dict:
    """Extract the custom request headers the MCP form stores under
    ``meta_data.http_headers`` (e.g. ClickUp's ``x-workspace-id``).

    These live in meta_data (not auth_config), so ``build_auth_headers`` never sees them — they
    must be merged into the request headers explicitly at validation and call time.
    """
    if not meta_data:
        return {}
    http_headers = meta_data.get("http_headers")
    if isinstance(http_headers, dict):
        return {k: v for k, v in http_headers.items() if k and v}
    return {}


class McpServerService(BaseService):

    VALID_TRANSPORT_TYPES = {"sse", "streamable_http"}

    def _validate_auth_type(self, auth_type: Optional[str]) -> str:
        """Normalize + validate the incoming ``auth_type``.

        Empty / missing is treated as ``'none'`` so callers can omit the field.
        Rejects unknown values so the DB never grows a mystery auth-mode.
        """
        normalized = normalize_auth_type(auth_type)
        if normalized not in VALID_AUTH_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid auth_type '{auth_type}'. "
                    f"Must be one of: {sorted(VALID_AUTH_TYPES)}"
                ),
            )
        return normalized

    def _check_duplicate_name(self, name: str, exclude_id=None) -> None:
        query = self.query(McpServer).filter(McpServer.name == name)
        if exclude_id is not None:
            query = query.filter(McpServer.id != exclude_id)
        if query.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An MCP server with name '{name}' already exists in this organization",
            )

    def _sync_mcp_tools(self, mcp_server: McpServer, discovered_tools: list) -> None:
        """Sync discovered MCP tools into the tools table."""
        existing_tools = (
            self.db.query(Tool)
            .filter(Tool.mcp_server_id == mcp_server.id, Tool.organization_id == self.org_id)
            .all()
        )
        existing_map = {t.name: t for t in existing_tools}
        discovered_names = {t["name"] for t in discovered_tools}

        # Delete tools no longer present
        for name, tool in existing_map.items():
            if name not in discovered_names:
                self.db.delete(tool)

        now = datetime.now(timezone.utc)
        for dt in discovered_tools:
            params = {"properties": dt.get("parameters", {}), "required": dt.get("required", [])}
            if dt["name"] in existing_map:
                # Update if changed
                existing_tool = existing_map[dt["name"]]
                if existing_tool.description != (dt.get("description") or "") or existing_tool.parameters != params:
                    existing_tool.description = dt.get("description") or ""
                    existing_tool.parameters = params
                    existing_tool.updated_at = now
            else:
                # Create new
                tool = Tool(
                    id=uuid_lib.uuid4(),
                    name=dt["name"],
                    description=dt.get("description") or "",
                    tool_type="mcp",
                    parameters=params,
                    mcp_server_id=mcp_server.id,
                    organization_id=self.org_id,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(tool)

        self.db.commit()

    def _validate_transport_type(self, transport_type: str) -> None:
        if transport_type not in self.VALID_TRANSPORT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transport_type '{transport_type}'. Must be one of: {', '.join(self.VALID_TRANSPORT_TYPES)}",
            )

    async def upsert_mcp_server(self, data: Dict[str, Any]) -> McpServer:
        """Create or update an MCP server. Send id to update; send name and server_url to create.

        Optional ``agent_ids``: when present, the server's published-version
        attachments are full-synced to exactly that agent list after the row is
        saved (absent key = attachments untouched). Sync problems are reported
        via the transient ``attachment_warnings`` attribute, not raised."""
        # Popped before the field loops below so it can never be setattr'd
        # onto the row.
        agent_ids = data.pop("agent_ids", None)
        mcp_server_id = data.get("id")
        now = datetime.now(timezone.utc)

        if mcp_server_id is not None:
            existing = self.query(McpServer).filter(McpServer.id == mcp_server_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="MCP server not found",
                )
            update_data = {k: v for k, v in data.items() if k != "id"}
            if "name" in update_data:
                self._check_duplicate_name(update_data["name"], exclude_id=mcp_server_id)
            if "transport_type" in update_data:
                self._validate_transport_type(update_data["transport_type"])
            if "auth_type" in update_data:
                update_data["auth_type"] = self._validate_auth_type(update_data["auth_type"])

            # Resolve the effective OAuth connection (incoming value wins, else the stored one)
            # and block the update early if it lacks the provider's required scopes or points at
            # a different provider than the MCP server itself (e.g. Google Calendar OAuth linked
            # to a HubSpot MCP).
            effective_oauth_id = update_data.get("oauth_connection_id", existing.oauth_connection_id)
            effective_app_integration_id = update_data.get(
                "app_integration_id", existing.app_integration_id
            )
            if "oauth_connection_id" in update_data or "app_integration_id" in update_data:
                self._validate_oauth_provider_match(
                    effective_app_integration_id, effective_oauth_id
                )
            if "oauth_connection_id" in update_data:
                self._validate_oauth_scopes(effective_oauth_id)

            # Validate connection if connection-related fields changed
            connection_fields = {"server_url", "transport_type", "auth_config", "oauth_connection_id", "auth_type"}
            validation_result = None
            if connection_fields & update_data.keys():
                validate_transport = update_data.get("transport_type", existing.transport_type)
                if "auth_config" in update_data:
                    update_data["auth_config"] = strip_masked_secret_url(
                        update_data["auth_config"], existing.auth_config
                    )
                    validate_auth = update_data["auth_config"]
                else:
                    validate_auth = decrypt_auth_config(existing.auth_config)
                validate_url = effective_server_url(
                    validate_auth, update_data.get("server_url", existing.server_url)
                )
                effective_meta = update_data.get("meta_data", existing.meta_data)
                effective_auth_type = update_data.get("auth_type", existing.auth_type)
                # OAuth bearer takes precedence over any custom header of the same name.
                oauth_headers = await run_in_threadpool(
                    self._resolve_oauth_headers, effective_oauth_id
                )
                extra_headers = {
                    **headers_from_meta(effective_meta),
                    **oauth_headers,
                }
                validation_result = await self.validate_mcp_connection(
                    validate_url, validate_transport, validate_auth,
                    extra_headers=extra_headers, auth_type=effective_auth_type,
                )

            if "auth_config" in update_data:
                update_data["auth_config"] = encrypt_auth_config(update_data["auth_config"])
            for key, value in update_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            # A successful (re)validation proves the server is reachable and authenticated. If a
            # prior OAuth disconnect had auto-deactivated it (delete_connection sets is_active=False
            # + nulls oauth_connection_id), bring it back online here — unless the caller explicitly
            # set is_active in this request. Without this, re-linking a working connection silently
            # leaves the server inactive, so it never loads for the agent at call time.
            if validation_result is not None and "is_active" not in update_data:
                existing.is_active = True
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            if validation_result:
                self._sync_mcp_tools(existing, validation_result["tools"])
            if agent_ids is not None:
                self._sync_agent_attachments(existing, agent_ids)
            return existing

        # Create new MCP server
        if not data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required when creating a new MCP server",
            )
        if not data.get("server_url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="server_url is required when creating a new MCP server",
            )
        self._check_duplicate_name(data["name"])
        transport_type = data.get("transport_type", "streamable_http")
        self._validate_transport_type(transport_type)
        auth_type = self._validate_auth_type(data.get("auth_type"))

        # Block creation early if a linked OAuth connection is wrong-provider (e.g. Google
        # Calendar OAuth attached to a HubSpot MCP) or lacks required scopes.
        oauth_connection_id = data.get("oauth_connection_id")
        app_integration_id = data.get("app_integration_id")
        self._validate_oauth_provider_match(app_integration_id, oauth_connection_id)
        self._validate_oauth_scopes(oauth_connection_id)

        # Validate connection before persisting (inject custom headers + OAuth bearer when linked).
        oauth_headers = await run_in_threadpool(
            self._resolve_oauth_headers, oauth_connection_id
        )
        extra_headers = {
            **headers_from_meta(data.get("meta_data")),
            **oauth_headers,
        }
        validation_result = await self.validate_mcp_connection(
            effective_server_url(data.get("auth_config"), data["server_url"]),
            transport_type, data.get("auth_config"),
            extra_headers=extra_headers, auth_type=auth_type,
        )

        mcp_server = McpServer(
            id=uuid_lib.uuid4(),
            name=data["name"],
            description=data.get("description"),
            server_url=data["server_url"],
            endpoint=data.get("endpoint"),
            icon=data.get("icon"),
            transport_type=transport_type,
            auth_type=auth_type,
            auth_config=encrypt_auth_config(data.get("auth_config")),
            meta_data=data.get("meta_data"),
            oauth_connection_id=oauth_connection_id,
            app_integration_id=data.get("app_integration_id"),
            is_active=data.get("is_active", True),
            organization_id=self.org_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(mcp_server)
        self.db.commit()
        self.db.refresh(mcp_server)
        self._sync_mcp_tools(mcp_server, validation_result["tools"])
        if agent_ids is not None:
            self._sync_agent_attachments(mcp_server, agent_ids)
        return mcp_server

    def _sync_agent_attachments(self, mcp_server: McpServer, agent_ids: List) -> None:
        """Full-sync the server's published-version attachments to ``agent_ids``.

        Companion to ``upsert_mcp_server``'s optional ``agent_ids`` field.
        Delegates to the shared ``sync_agent_attachments`` helper (behaviour
        documented there), passing this service's own ``attach_to_agents`` /
        ``detach_from_agents`` so published-version resolution, scope validation,
        and audit logging stay in one place. Stamps the transient
        ``attachment_warnings`` / ``attachment_summary`` attributes onto
        ``mcp_server`` for the response layer.
        """
        warnings, summary = sync_agent_attachments(
            self.db,
            self.org_id,
            link_model=AgentMcpServer,
            link_fk=AgentMcpServer.mcp_server_id,
            entity_id=mcp_server.id,
            agent_ids=agent_ids,
            attach=lambda ids: (self.attach_to_agents(mcp_server.id, ids), len(ids))[1],
            detach=lambda ids: (self.detach_from_agents(mcp_server.id, ids), len(ids))[1],
        )
        mcp_server.attachment_warnings = warnings
        mcp_server.attachment_summary = summary

    def get_agents_by_mcp_server(self, mcp_server_id) -> List[Dict[str, str]]:
        """Agents whose PUBLISHED version reaches this server — the same scope
        ``_sync_agent_attachments`` reads and writes, so the edit form can
        round-trip the list without drift."""
        self.get_mcp_server(mcp_server_id)
        return get_attached_agents(
            self.db,
            self.org_id,
            link_model=AgentMcpServer,
            link_fk=AgentMcpServer.mcp_server_id,
            entity_id=mcp_server_id,
        )

    # ``status`` is derived from the boolean ``is_active`` via a CASE expression
    # so it flows through the generic faceted-query helpers as a string facet.
    MCP_FACET_FIELDS = ["status", "transport_type"]

    def _mcp_column_map(self) -> Dict[str, Any]:
        return {
            "name": McpServer.name,
            "status": case((McpServer.is_active.is_(True), "active"), else_="inactive"),
            "is_active": McpServer.is_active,
            "transport_type": McpServer.transport_type,
            "created_at": McpServer.created_at,
            "updated_at": McpServer.updated_at,
        }

    def list_mcp_servers(
        self,
        search: str = None,
        is_active: bool = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = None,
        filters: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """List MCP servers with search, filter, sort, and pagination.

        Returns {"data": [...], "pagination": {...}}.
        """
        column_map = self._mcp_column_map()
        query = self.query(McpServer)

        if search:
            query = query.filter(
                or_(
                    McpServer.name.ilike(f"%{search}%"),
                    McpServer.description.ilike(f"%{search}%"),
                    McpServer.server_url.ilike(f"%{search}%"),
                )
            )

        if is_active is not None:
            query = query.filter(McpServer.is_active == is_active)

        query = apply_filters(query, filters, column_map)

        total = query.count()

        # Secondary order by id keeps pagination stable across equal sort keys.
        ordered_query = apply_sort(
            query, column_map, sort_by, sort_order, McpServer.created_at
        ).order_by(McpServer.id)

        if page_size is not None:
            offset = (page - 1) * page_size
            servers = ordered_query.offset(offset).limit(page_size).all()
        else:
            servers = ordered_query.all()

        # Batch-hydrate OAuth summaries once per list response so the UI
        # can render token-expiry badges without N+1 lookups on the card
        # grid. Same pattern as ``ToolService.list_tools``.
        oauth_map = self._hydrate_oauth_summary(
            [s.oauth_connection_id for s in servers if s.oauth_connection_id]
        )
        data = [self.mcp_server_response(s, oauth_map=oauth_map) for s in servers]

        if page_size is not None:
            total_pages = (total + page_size - 1) // page_size
        else:
            total_pages = 1

        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size if page_size is not None else total,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def _hydrate_oauth_summary(self, connection_ids) -> Dict[Any, Dict[str, Any]]:
        """Wrap ``OAuthService.hydrate_summary_by_ids`` so ``mcp_server_response``
        can stay ignorant of OAuthService construction details. Kept as an
        instance method so the tenant scope flows automatically."""
        if not connection_ids:
            return {}
        from core.services.oauth_service import OAuthService

        oauth_svc = OAuthService(self.db, org_id=self.org_id)
        return oauth_svc.hydrate_summary_by_ids(connection_ids)

    def get_facets(self, filters: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        return build_facets(
            lambda: self.query(McpServer),
            self._mcp_column_map(),
            self.MCP_FACET_FIELDS,
            filters,
        )

    def get_filter_values(self, column_name: str) -> Dict[str, Any]:
        column_map = self._mcp_column_map()
        allowed = {k: column_map[k] for k in ("name", "status", "transport_type")}
        return distinct_values(self.query(McpServer), allowed, column_name)

    def get_mcp_server(self, mcp_server_id) -> McpServer:
        mcp_server = self.query(McpServer).filter(McpServer.id == mcp_server_id).first()
        if not mcp_server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found",
            )
        return mcp_server

    def delete_mcp_server(self, mcp_server_id) -> Dict[str, str]:
        mcp_server = self.get_mcp_server(mcp_server_id)
        self.db.delete(mcp_server)
        self.db.commit()
        return {"message": "MCP server deleted successfully"}

    def attach_to_agents(self, mcp_server_id, agent_ids: List) -> None:
        from sqlalchemy import tuple_

        from core.models.agent import Agent

        mcp_server = self.get_mcp_server(mcp_server_id)
        # An MCP server backed by an OAuth connection must have all required scopes before it can
        # be wired onto an agent — otherwise tool discovery silently no-ops during a live call.
        self._validate_oauth_scopes(mcp_server.oauth_connection_id)

        # Per-version attachments: attach to each agent's published config.
        published_map = {
            aid: cid
            for aid, cid in self.db.query(Agent.id, Agent.published_config_id)
            .filter(Agent.id.in_(agent_ids))
            .all()
            if cid is not None
        }

        # Reject up-front when every requested agent lacks a published version
        # — otherwise the empty case falls through to the generic "already
        # attached" error, which misleads the caller.
        if not published_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "None of the specified agents have a published version to attach to."
                    " Publish each agent first, then retry."
                ),
            )

        agent_config_pairs = list(published_map.items())
        already_attached = {
            row.agent_id
            for row in self.db.query(AgentMcpServer.agent_id)
            .filter(
                AgentMcpServer.mcp_server_id == mcp_server_id,
                tuple_(AgentMcpServer.agent_id, AgentMcpServer.agent_config_id).in_(
                    agent_config_pairs
                ),
            )
            .all()
        }

        new_ids = [aid for aid in published_map if aid not in already_attached]
        if not new_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCP server is already attached to all specified agents",
            )
        now = datetime.now(timezone.utc)
        for agent_id in new_ids:
            self.db.add(AgentMcpServer(
                agent_id=agent_id,
                mcp_server_id=mcp_server_id,
                agent_config_id=published_map[agent_id],
                organization_id=self.org_id,
                created_at=now,
                updated_at=now,
            ))
            self.audit.log(
                AgentAuditAction.MCP_ATTACHED,
                agent_id=agent_id,
                agent_config_id=published_map[agent_id],
                target_resource_type=AuditResourceType.MCP_SERVER,
                target_resource_id=str(mcp_server_id),
            )
        self.db.commit()

    def detach_from_agents(self, mcp_server_id, agent_ids: List) -> Dict[str, str]:
        from core.models.agent import Agent

        # Detach scoped to each agent's published config — historical version
        # links stay intact for version history.
        published_ids = [
            cid
            for (cid,) in self.db.query(Agent.published_config_id)
            .filter(Agent.id.in_(agent_ids))
            .all()
            if cid is not None
        ]
        if not published_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server is not attached to any of the specified agents",
            )
        links = (
            self.db.query(AgentMcpServer)
            .filter(
                AgentMcpServer.mcp_server_id == mcp_server_id,
                AgentMcpServer.agent_id.in_(agent_ids),
                AgentMcpServer.agent_config_id.in_(published_ids),
            )
            .all()
        )
        if not links:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server is not attached to any of the specified agents",
            )
        for link in links:
            self.audit.log(
                AgentAuditAction.MCP_DETACHED,
                agent_id=link.agent_id,
                agent_config_id=link.agent_config_id,
                target_resource_type=AuditResourceType.MCP_SERVER,
                target_resource_id=str(mcp_server_id),
            )
            self.db.delete(link)
        self.db.commit()
        return {"message": f"MCP server detached from {len(links)} agent(s) successfully"}

    def get_mcp_servers_by_agent(self, agent_id) -> List[Dict[str, Any]]:
        # Per-version: only return the agent's published-version MCP servers.
        from core.utils.agent_scope import published_config_subquery

        published_config_sq = published_config_subquery(agent_id)
        rows = (
            self.db.query(McpServer)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(
                AgentMcpServer.agent_id == agent_id,
                AgentMcpServer.agent_config_id == published_config_sq,
                McpServer.is_active == True,
                McpServer.organization_id == self.org_id,
            )
            .all()
        )
        return [self.mcp_server_response(server) for server in rows]

    def _resolve_oauth_headers(self, oauth_connection_id) -> Dict[str, str]:
        """Resolve the auth header from a linked connection.

        For OAuth / bearer / client-credentials connections this is a fresh
        ``Authorization: Bearer`` header; for API-key connections it is the
        credential's custom header (e.g. ``X-API-Key: <key>``). Returns ``{}``
        when no connection is linked. Raises HTTPException(400) when the
        connection is missing or its credential can't be resolved, so the
        failure is visible at config time rather than silently producing an
        unauthenticated server that discovers zero tools at call time.
        """
        if not oauth_connection_id:
            return {}
        from core.services.oauth_service import OAuthService

        svc = OAuthService(self.db, org_id=self.org_id)
        connection = svc.get_connection(oauth_connection_id)  # 404 if missing
        header_name, header_value = svc.resolve_connection_auth_header(connection)
        return {header_name: header_value}

    def build_validation_headers(
        self, meta_data, oauth_connection_id
    ) -> Dict[str, str]:
        """Assemble the request headers used to validate an MCP connection.

        Reflects how the server will actually authenticate at call time: custom
        headers stored under ``meta_data.http_headers`` merged with a fresh OAuth
        bearer (or API-key header) from the linked connection, which wins on
        name conflict. Public entrypoint so routers don't reach into the private
        header resolvers — the same assembly ``upsert_mcp_server`` /
        ``discover_tools`` perform inline.
        """
        return {
            **headers_from_meta(meta_data),
            **self._resolve_oauth_headers(oauth_connection_id),
        }

    def _validate_oauth_scopes(self, oauth_connection_id) -> None:
        """Block config when a linked connection lacks the provider's required scopes."""
        if not oauth_connection_id:
            return
        from core.services.oauth_service import OAuthService

        svc = OAuthService(self.db, org_id=self.org_id)
        connection = svc.get_connection(oauth_connection_id)
        svc.raise_if_missing_scopes(svc.validate_connection_for_provider(connection))

    def _validate_oauth_provider_match(
        self, app_integration_id, oauth_connection_id
    ) -> None:
        """Block config when the linked OAuth connection is for a different
        provider than the MCP server itself.

        e.g. a Google Calendar connection linked to a HubSpot MCP would
        trivially pass every other check (the token refreshes, the connection's
        own scopes are present) but the HubSpot server rejects every request
        at call time. Compare ``app_integration_id`` on both sides and fail
        fast at save time so the bad config never persists.

        No-op when either side lacks an ``app_integration_id`` — generic /
        custom MCP servers outside the app catalog can still link an arbitrary
        connection, matching the pre-existing behavior.
        """
        if not oauth_connection_id or not app_integration_id:
            return
        from core.models.app_integration import AppIntegration
        from core.services.oauth_service import OAuthService

        svc = OAuthService(self.db, org_id=self.org_id)
        connection = svc.get_connection(oauth_connection_id)
        if not connection.app_integration_id:
            return
        if str(connection.app_integration_id) == str(app_integration_id):
            return
        server_app = self.query(AppIntegration).filter(
            AppIntegration.id == app_integration_id
        ).first()
        conn_app = self.query(AppIntegration).filter(
            AppIntegration.id == connection.app_integration_id
        ).first()
        server_name = server_app.display_name if server_app else "this MCP server"
        conn_name = conn_app.display_name if conn_app else "a different provider"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The linked OAuth connection is for {conn_name} but this "
                f"MCP server is for {server_name}. Link a {server_name} "
                f"connection instead."
            ),
        )

    async def validate_mcp_connection(
        self,
        server_url: str,
        transport_type: str,
        auth_config: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
        auth_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Connect to an MCP server with raw (unencrypted) config and return its tools.

        ``auth_type`` selects the header-building branch (see :func:`build_auth_headers`).
        When ``None``, the header builder falls back to legacy inference so existing rows
        keep validating the same way they did before this column existed.

        Raises HTTPException(400) on failure."""
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.streamable_http import streamablehttp_client

        self._validate_transport_type(transport_type)
        headers = (
            build_auth_headers(auth_config, already_decrypted=True, auth_type=auth_type)
            if auth_config
            else {}
        )
        if extra_headers:
            # OAuth-resolved bearer (or other dynamic auth) takes precedence over static headers.
            headers = {**headers, **extra_headers}

        try:
            if transport_type == "sse":
                async with sse_client(url=server_url, headers=headers) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
            elif transport_type == "streamable_http":
                async with streamablehttp_client(url=server_url, headers=headers) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
        except HTTPException:
            raise
        except Exception as e:
            # Full traceback for diagnosis; no secrets — auth_config, resolved
            # headers, and the (possibly secret) server_url are deliberately
            # omitted. The client still gets the sanitized HTTPException below.
            logger.exception(
                f"[mcp] MCP connection validation failed (transport={transport_type})"
            )
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in [
                "nodename nor servname", "name or service not known",
                "no such host", "getaddrinfo failed", "invalid url",
                "url", "connection refused", "connect call failed",
                "unreachable", "timeout", "timed out",
            ]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid server URL. Please check the URL and try again.",
                )
            if any(keyword in error_str for keyword in [
                "401", "403", "unauthorized", "forbidden",
                "authentication", "auth", "token", "api key",
            ]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Authentication failed. Please check your token or API key and try again.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to MCP server: {str(e)}",
            )

        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema.get("properties", {}),
                "required": tool.inputSchema.get("required", []),
            })

        return {"tools": tools, "tool_count": len(tools)}

    async def discover_tools(self, mcp_server_id) -> Dict[str, Any]:
        """Connect to an MCP server and return its available tools."""
        mcp_server = self.get_mcp_server(mcp_server_id)
        decrypted_auth = decrypt_auth_config(mcp_server.auth_config)
        oauth_headers = await run_in_threadpool(
            self._resolve_oauth_headers, mcp_server.oauth_connection_id
        )
        extra_headers = {
            **headers_from_meta(mcp_server.meta_data),
            **oauth_headers,
        }
        result = await self.validate_mcp_connection(
            resolve_server_url(mcp_server),
            mcp_server.transport_type,
            decrypted_auth,
            extra_headers=extra_headers,
            auth_type=mcp_server.auth_type,
        )
        self._sync_mcp_tools(mcp_server, result["tools"])
        return {
            "server_name": mcp_server.name,
            "server_url": mcp_server.server_url,
            "transport_type": mcp_server.transport_type,
            **result,
        }

    def mcp_server_response(
        self,
        mcp_server: McpServer,
        oauth_map: Optional[Dict[Any, Dict[str, Any]]] = None,
        *,
        mask_secrets: bool = True,
    ) -> Dict[str, Any]:
        # ``oauth_map`` is the pre-hydrated OAuth summary produced by
        # ``_hydrate_oauth_summary`` during list responses; single-item
        # responses can omit it and the nested block simply stays ``None``.
        oauth_connection = None
        if mcp_server.oauth_connection_id and oauth_map:
            oauth_connection = oauth_map.get(mcp_server.oauth_connection_id)
        # Safe by default: broad/list responses mask secret VALUES (keys kept)
        # so credentials are never dumped. Only the single-item edit-fetch
        # (get_mcp_server) passes ``mask_secrets=False`` to return the real
        # decrypted config the edit form needs to pre-fill.
        auth_config = (
            _masked_auth_config(mcp_server.auth_config)
            if mask_secrets
            else mask_auth_config_url(decrypt_auth_config(mcp_server.auth_config))
        )
        return {
            "id": str(mcp_server.id),
            "name": mcp_server.name,
            "description": mcp_server.description,
            "server_url": mcp_server.server_url,
            "endpoint": mcp_server.endpoint,
            "icon": mcp_server.icon,
            "transport_type": mcp_server.transport_type,
            "auth_type": normalize_auth_type(mcp_server.auth_type),
            "auth_config": auth_config,
            "meta_data": mcp_server.meta_data,
            "oauth_connection_id": (
                str(mcp_server.oauth_connection_id) if mcp_server.oauth_connection_id else None
            ),
            # Compact summary the UI uses to render the token-expiry badge
            # + "Test connection" button on the MCP card footer. ``None``
            # when the server has no OAuth link OR the connection wasn't
            # hydrated (single-item response paths).
            "oauth_connection": oauth_connection,
            "app_integration_id": (
                str(mcp_server.app_integration_id) if mcp_server.app_integration_id else None
            ),
            "is_active": mcp_server.is_active,
            "created_at": mcp_server.created_at,
            "updated_at": mcp_server.updated_at,
        }
