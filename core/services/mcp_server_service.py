import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi import HTTPException, status

from sqlalchemy import asc, desc, or_

from core.services.base import BaseService
from core.models.mcp_server import McpServer
from core.models.agent_mcp_server import AgentMcpServer
from core.models.tool import Tool
from core.utils.encryption import encrypt, decrypt


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


def build_auth_headers(auth_config, already_decrypted=False) -> dict:
    """Build HTTP headers from auth_config.

    All auth sources are MERGED (not mutually exclusive), because the UI lets a
    server use an API key / bearer token AND custom HTTP headers at the same time
    (e.g. ClickUp: ``Authorization: Bearer <key>`` plus ``x-workspace-id``).
    Explicit custom headers win on name conflicts; the api_key/token only fills
    ``Authorization`` if a custom header hasn't already set it.
    """
    if not auth_config:
        return {}
    decrypted = auth_config if already_decrypted else decrypt_auth_config(auth_config)
    headers = {}

    # 1) Explicit custom headers (list form), e.g. x-workspace-id
    if isinstance(decrypted.get("headers"), list):
        for h in decrypted["headers"]:
            if h.get("header_name") and h.get("header_value"):
                headers[h["header_name"]] = h["header_value"]

    # 2) Single header_name/header_value pair (legacy single-header form)
    if decrypted.get("header_name") and decrypted.get("header_value"):
        headers.setdefault(decrypted["header_name"], decrypted["header_value"])

    # 3) API key / bearer token → a CONFIGURABLE header + scheme, so this works for
    #    any provider instead of being hardcoded to "Authorization: Bearer".
    #      default                         -> Authorization: Bearer <secret>
    #      auth_header="X-Api-Key", scheme="" -> X-Api-Key: <secret>      (e.g. Postman)
    #      auth_scheme=""                  -> Authorization: <secret>     (e.g. ClickUp raw token)
    #      auth_scheme="Basic"             -> Authorization: Basic <secret>
    #    Only applied if that header wasn't already set by a custom header above.
    secret = decrypted.get("api_key") or decrypted.get("token") or decrypted.get("bearer_token")
    if secret:
        target = decrypted.get("auth_header") or decrypted.get("api_key_header") or "Authorization"
        scheme = decrypted.get("auth_scheme")
        if scheme is None:
            scheme = "Bearer"
        value = f"{scheme} {secret}".strip() if scheme else str(secret)
        if not any(k.lower() == target.lower() for k in headers):
            headers[target] = value

    return headers


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
        """Create or update an MCP server. Send id to update; send name and server_url to create."""
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

            # Resolve the effective OAuth connection (incoming value wins, else the stored one)
            # and block the update early if it lacks the provider's required scopes.
            effective_oauth_id = update_data.get("oauth_connection_id", existing.oauth_connection_id)
            if "oauth_connection_id" in update_data:
                self._validate_oauth_scopes(effective_oauth_id)

            # Validate connection if connection-related fields changed
            connection_fields = {"server_url", "transport_type", "auth_config", "oauth_connection_id"}
            validation_result = None
            if connection_fields & update_data.keys():
                validate_url = update_data.get("server_url", existing.server_url)
                validate_transport = update_data.get("transport_type", existing.transport_type)
                if "auth_config" in update_data:
                    validate_auth = update_data["auth_config"]
                else:
                    validate_auth = decrypt_auth_config(existing.auth_config)
                effective_meta = update_data.get("meta_data", existing.meta_data)
                # OAuth bearer takes precedence over any custom header of the same name.
                extra_headers = {
                    **headers_from_meta(effective_meta),
                    **self._resolve_oauth_headers(effective_oauth_id),
                }
                validation_result = await self.validate_mcp_connection(
                    validate_url, validate_transport, validate_auth, extra_headers=extra_headers
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

        # Block creation early if a linked OAuth connection lacks required scopes.
        oauth_connection_id = data.get("oauth_connection_id")
        self._validate_oauth_scopes(oauth_connection_id)

        # Validate connection before persisting (inject custom headers + OAuth bearer when linked).
        extra_headers = {
            **headers_from_meta(data.get("meta_data")),
            **self._resolve_oauth_headers(oauth_connection_id),
        }
        validation_result = await self.validate_mcp_connection(
            data["server_url"], transport_type, data.get("auth_config"),
            extra_headers=extra_headers,
        )

        mcp_server = McpServer(
            id=uuid_lib.uuid4(),
            name=data["name"],
            description=data.get("description"),
            server_url=data["server_url"],
            endpoint=data.get("endpoint"),
            icon=data.get("icon"),
            transport_type=transport_type,
            auth_config=encrypt_auth_config(data.get("auth_config")),
            meta_data=data.get("meta_data"),
            oauth_connection_id=oauth_connection_id,
            is_active=data.get("is_active", True),
            organization_id=self.org_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(mcp_server)
        self.db.commit()
        self.db.refresh(mcp_server)
        self._sync_mcp_tools(mcp_server, validation_result["tools"])
        return mcp_server

    def list_mcp_servers(
        self,
        search: str = None,
        is_active: bool = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = None,
    ) -> Dict[str, Any]:
        """List MCP servers with search, filter, sort, and pagination.

        Returns {"data": [...], "pagination": {...}}.
        """
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

        total = query.count()

        sort_column_map = {
            "created_at": McpServer.created_at,
            "updated_at": McpServer.updated_at,
            "name": McpServer.name,
        }
        sort_column = sort_column_map.get(sort_by, McpServer.created_at)
        order_func = asc if sort_order == "asc" else desc
        ordered_query = query.order_by(order_func(sort_column), McpServer.id)

        if page_size is not None:
            offset = (page - 1) * page_size
            servers = ordered_query.offset(offset).limit(page_size).all()
        else:
            servers = ordered_query.all()

        data = [self.mcp_server_response(s) for s in servers]

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
        mcp_server = self.get_mcp_server(mcp_server_id)
        # An MCP server backed by an OAuth connection must have all required scopes before it can
        # be wired onto an agent — otherwise tool discovery silently no-ops during a live call.
        self._validate_oauth_scopes(mcp_server.oauth_connection_id)
        existing = (
            self.db.query(AgentMcpServer.agent_id)
            .filter(AgentMcpServer.mcp_server_id == mcp_server_id, AgentMcpServer.agent_id.in_(agent_ids))
            .all()
        )
        existing_ids = {row[0] for row in existing}
        new_ids = [aid for aid in agent_ids if aid not in existing_ids]
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
                created_at=now,
                updated_at=now,
            ))
        self.db.commit()

    def detach_from_agents(self, mcp_server_id, agent_ids: List) -> Dict[str, str]:
        links = (
            self.db.query(AgentMcpServer)
            .filter(AgentMcpServer.mcp_server_id == mcp_server_id, AgentMcpServer.agent_id.in_(agent_ids))
            .all()
        )
        if not links:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server is not attached to any of the specified agents",
            )
        for link in links:
            self.db.delete(link)
        self.db.commit()
        return {"message": f"MCP server detached from {len(links)} agent(s) successfully"}

    def get_mcp_servers_by_agent(self, agent_id) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(McpServer)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(
                AgentMcpServer.agent_id == agent_id,
                McpServer.is_active == True,
                McpServer.organization_id == self.org_id,
            )
            .all()
        )
        return [self.mcp_server_response(server) for server in rows]

    def _resolve_oauth_headers(self, oauth_connection_id) -> Dict[str, str]:
        """Resolve a fresh ``Authorization: Bearer`` header from a linked OAuth connection.

        Returns ``{}`` when no connection is linked. Raises HTTPException(400) when the connection
        is missing or its token can't be obtained, so the failure is visible at config time rather
        than silently producing an unauthenticated server that discovers zero tools at call time.
        """
        if not oauth_connection_id:
            return {}
        from core.services.oauth_service import OAuthService

        svc = OAuthService(self.db, org_id=self.org_id)
        connection = svc.get_connection(oauth_connection_id)  # 404 if missing
        token = svc.get_valid_access_token_for_connection(connection)
        return {"Authorization": f"Bearer {token}"}

    def _validate_oauth_scopes(self, oauth_connection_id) -> None:
        """Block config when a linked connection lacks the provider's required scopes."""
        if not oauth_connection_id:
            return
        from core.services.oauth_service import OAuthService

        svc = OAuthService(self.db, org_id=self.org_id)
        connection = svc.get_connection(oauth_connection_id)
        svc.raise_if_missing_scopes(svc.validate_connection_for_provider(connection))

    async def validate_mcp_connection(
        self,
        server_url: str,
        transport_type: str,
        auth_config: dict = None,
        extra_headers: dict = None,
    ) -> Dict[str, Any]:
        """Connect to an MCP server with raw (unencrypted) config and return its tools.
        Raises HTTPException(400) on failure."""
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.streamable_http import streamablehttp_client

        self._validate_transport_type(transport_type)
        headers = build_auth_headers(auth_config, already_decrypted=True) if auth_config else {}
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
        result = await self.validate_mcp_connection(
            mcp_server.server_url, mcp_server.transport_type, decrypted_auth
        )
        self._sync_mcp_tools(mcp_server, result["tools"])
        return {
            "server_name": mcp_server.name,
            "server_url": mcp_server.server_url,
            "transport_type": mcp_server.transport_type,
            **result,
        }

    def mcp_server_response(self, mcp_server: McpServer) -> Dict[str, Any]:
        return {
            "id": str(mcp_server.id),
            "name": mcp_server.name,
            "description": mcp_server.description,
            "server_url": mcp_server.server_url,
            "endpoint": mcp_server.endpoint,
            "icon": mcp_server.icon,
            "transport_type": mcp_server.transport_type,
            "auth_config": decrypt_auth_config(mcp_server.auth_config),
            "meta_data": mcp_server.meta_data,
            "oauth_connection_id": (
                str(mcp_server.oauth_connection_id) if mcp_server.oauth_connection_id else None
            ),
            "is_active": mcp_server.is_active,
            "created_at": mcp_server.created_at,
            "updated_at": mcp_server.updated_at,
        }
