import json
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import case, or_

from core.services.audit_actions import AgentAuditAction, AuditResourceType
from core.services.base import BaseService
from core.models.tool import Tool
from core.models.agent_tool import AgentTool
from core.utils.encryption import encrypt, decrypt
from core.utils.faceted_query import apply_filters, apply_sort, build_facets, distinct_values
from core.utils.list_params import resolve_sort


def encrypt_auth_config(auth_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Encrypt all string values in auth_config before storing in DB."""
    if not auth_config:
        return auth_config
    encrypted = {}
    for key, value in auth_config.items():
        if isinstance(value, str) and value:
            encrypted[key] = encrypt(value)
        else:
            encrypted[key] = value
    return encrypted


def decrypt_auth_config(auth_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Decrypt all string values in auth_config when reading from DB."""
    if not auth_config:
        return auth_config
    decrypted = {}
    for key, value in auth_config.items():
        if isinstance(value, str) and value:
            try:
                decrypted[key] = decrypt(value)
            except Exception:
                # Value may not be encrypted (e.g. legacy data), return as-is
                decrypted[key] = value
        else:
            decrypted[key] = value
    return decrypted


class ToolService(BaseService):

    def _validate_oauth_connection(self, oauth_connection_id) -> None:
        """Raise 400 if the OAuth connection doesn't exist or belongs to a different org."""
        from core.models.oauth_connection import OAuthConnection

        connection = self.db.query(OAuthConnection).filter(
            OAuthConnection.id == oauth_connection_id,
        ).first()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth connection {oauth_connection_id} not found",
            )
        if str(connection.organization_id) != str(self.org_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth connection does not belong to this organization",
            )

    def _validate_oauth_scopes(self, tool_type: Optional[str], oauth_connection_id) -> None:
        """Block config when a built-in tool's linked connection lacks the provider's scopes.

        No-op for tool types not governed by an OAuth provider (e.g. custom/webhook tools) or when
        no connection is linked.
        """
        if not oauth_connection_id:
            return
        from core.services.oauth_providers import get_provider_scopes, provider_for_tool_type
        from core.services.oauth_service import OAuthService

        provider = provider_for_tool_type(tool_type)
        if not provider:
            return
        svc = OAuthService(self.db, org_id=self.org_id)
        connection = svc.get_connection(oauth_connection_id)
        svc.raise_if_missing_scopes(
            svc.validate_scopes(connection, get_provider_scopes(self.db, self.org_id, provider))
        )

    def _check_duplicate_name(self, name: str, exclude_id=None) -> None:
        """Raise 409 if a tool with the same name already exists in this org."""
        query = self.query(Tool).filter(Tool.name == name, Tool.tool_type != 'mcp')
        if exclude_id is not None:
            query = query.filter(Tool.id != exclude_id)
        if query.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A tool with name '{name}' already exists in this organization",
            )

    def get_tools(self) -> List[Tool]:
        return self.query(Tool).filter(Tool.tool_type != 'mcp').all()

    def get_template_tools(self) -> List[Tool]:
        return self.query(Tool).filter(Tool.is_template == True).all()

    def get_tool(self, tool_id) -> Tool:
        tool = self.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found",
            )
        return tool

    def upsert_tool(self, data: Dict[str, Any]) -> Tool:
        """Create or update a tool. Send id to update; send name and description to create."""
        tool_id = data.get("id")
        now = datetime.now(timezone.utc)

        if tool_id is not None:
            existing = self.query(Tool).filter(Tool.id == tool_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tool not found",
                )
            if existing.is_template:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template tools cannot be edited",
                )
            # Built-in tools: only allow updating name, description, meta_data, auth_config, and is_active
            if existing.tool_type != "custom":
                allowed = {
                    "name", "description", "meta_data", "auth_config", "is_active",
                    "oauth_connection_id", "app_integration_id",
                }
                update_data = {k: v for k, v in data.items() if k in allowed}
            else:
                update_data = {k: v for k, v in data.items() if k != "id"}
            if update_data.get("oauth_connection_id"):
                self._validate_oauth_connection(update_data["oauth_connection_id"])
                self._validate_oauth_scopes(
                    existing.tool_type, update_data["oauth_connection_id"]
                )
            if "name" in update_data:
                self._check_duplicate_name(update_data["name"], exclude_id=tool_id)
            if "auth_config" in update_data:
                update_data["auth_config"] = encrypt_auth_config(update_data["auth_config"])
            for key, value in update_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new tool
        if not data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required when creating a new tool",
            )
        if not data.get("description"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="description is required when creating a new tool",
            )
        self._check_duplicate_name(data["name"])
        if data.get("oauth_connection_id"):
            self._validate_oauth_connection(data["oauth_connection_id"])
            self._validate_oauth_scopes(
                data.get("tool_type", "custom"), data["oauth_connection_id"]
            )
        tool = Tool(
            id=uuid_lib.uuid4(),
            name=data["name"],
            description=data["description"],
            tool_type=data.get("tool_type", "custom"),
            parameters=data.get("parameters", {}),
            url=data.get("url"),
            method=data.get("method", "POST"),
            auth_type=data.get("auth_type", "none"),
            auth_config=encrypt_auth_config(data.get("auth_config")),
            meta_data=data.get("meta_data"),
            oauth_connection_id=data.get("oauth_connection_id"),
            app_integration_id=data.get("app_integration_id"),
            is_active=data.get("is_active", True),
            organization_id=self.org_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def delete_tool(self, tool_id) -> Dict[str, str]:
        tool = self.get_tool(tool_id)
        if tool.is_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template tools cannot be deleted",
            )
        if tool.tool_type == 'mcp':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCP tools cannot be deleted directly. Delete the MCP server instead.",
            )
        # Remove the agent<->tool association rows so deleting a tool also
        # detaches it from every agent (no orphaned agent_tools records).
        self.db.query(AgentTool).filter(AgentTool.tool_id == tool.id).delete(
            synchronize_session=False
        )
        self.db.delete(tool)
        self.db.commit()
        return {"message": "Tool deleted successfully"}

    def attach_tool_to_agents(self, agent_ids: List, tool_id) -> List[AgentTool]:
        from sqlalchemy import tuple_

        from core.models.agent import Agent

        # Verify tool exists
        tool = self.get_tool(tool_id)
        # A built-in OAuth tool must have all required scopes before it's wired onto an agent,
        # so the agent never silently fails to act on it mid-call.
        self._validate_oauth_scopes(tool.tool_type, tool.oauth_connection_id)

        # Per-version attachments: each row must declare the config it belongs
        # to. The admin "attach to agents" action targets each agent's
        # published version (the one serving calls right now).
        published_map = {
            aid: cid
            for aid, cid in self.db.query(Agent.id, Agent.published_config_id)
            .filter(Agent.id.in_(agent_ids))
            .all()
            if cid is not None
        }

        # Reject up-front when every requested agent lacks a published version
        # — without this, the empty-published_map case falls through to the
        # generic "already attached" error, which misleads the caller.
        if not published_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "None of the specified agents have a published version to attach to."
                    " Publish each agent first, then retry."
                ),
            )

        # Already-attached lookup scoped to each agent's published config — an
        # agent whose published version already has this tool is a skip.
        agent_config_pairs = list(published_map.items())
        already_attached = {
            row.agent_id
            for row in self.db.query(AgentTool.agent_id)
            .filter(
                AgentTool.tool_id == tool_id,
                tuple_(AgentTool.agent_id, AgentTool.agent_config_id).in_(
                    agent_config_pairs
                ),
            )
            .all()
        }

        new_ids = [aid for aid in published_map if aid not in already_attached]

        if not new_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tool is already attached to all specified agents",
            )

        now = datetime.now(timezone.utc)
        agent_tools = [
            AgentTool(
                agent_id=aid,
                tool_id=tool_id,
                agent_config_id=published_map[aid],
                created_at=now,
                updated_at=now,
            )
            for aid in new_ids
        ]
        self.db.add_all(agent_tools)

        for at in agent_tools:
            self.audit.log(
                AgentAuditAction.TOOL_ATTACHED,
                agent_id=at.agent_id,
                agent_config_id=at.agent_config_id,
                target_resource_type=AuditResourceType.TOOL,
                target_resource_id=str(tool_id),
            )

        self.db.commit()
        return agent_tools

    def detach_tool_from_agents(self, agent_ids: List, tool_id) -> Dict[str, str]:
        from core.models.agent import Agent

        # Detach only removes the row scoped to each agent's published config —
        # historical version attachments stay intact so version history doesn't
        # silently lose tools.
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
                detail="Tool is not attached to any of the specified agents",
            )
        agent_tools = (
            self.db.query(AgentTool)
            .filter(
                AgentTool.tool_id == tool_id,
                AgentTool.agent_id.in_(agent_ids),
                AgentTool.agent_config_id.in_(published_ids),
            )
            .all()
        )
        if not agent_tools:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool is not attached to any of the specified agents",
            )
        for at in agent_tools:
            self.audit.log(
                AgentAuditAction.TOOL_DETACHED,
                agent_id=at.agent_id,
                agent_config_id=at.agent_config_id,
                target_resource_type=AuditResourceType.TOOL,
                target_resource_id=str(tool_id),
            )
            self.db.delete(at)
        self.db.commit()
        return {"message": f"Tool detached from {len(agent_tools)} agent(s) successfully"}

    def get_tools_by_agent(self, agent_id) -> List[Tool]:
        # Per-version attachments: only return the agent's published-version
        # tools so admin views and runtime callers see the same set the live
        # agent is using.
        from core.utils.agent_scope import published_config_subquery

        published_config_sq = published_config_subquery(agent_id)
        return (
            self.query(Tool)
            .join(AgentTool, AgentTool.tool_id == Tool.id)
            .filter(
                AgentTool.agent_id == agent_id,
                AgentTool.agent_config_id == published_config_sq,
                Tool.is_active == True,
            )
            .all()
        )

    # ------------------------------------------------------------------
    # Faceted list / facets / filter-values
    # ------------------------------------------------------------------

    # ``status`` is derived from the boolean ``is_active`` via a CASE expression
    # so it flows through the generic faceted-query helpers as a string facet.
    TOOL_FACET_FIELDS = ["tool_type", "status"]

    def _tool_column_map(self) -> Dict[str, Any]:
        return {
            "name": Tool.name,
            "tool_type": Tool.tool_type,
            "status": case((Tool.is_active.is_(True), "active"), else_="inactive"),
            "is_active": Tool.is_active,
            "created_at": Tool.created_at,
            "updated_at": Tool.updated_at,
        }

    def _tool_base_query(self):
        """Org-scoped base query for the tools list surface (no MCP, no templates)."""
        return self.query(Tool).filter(Tool.tool_type != 'mcp', Tool.is_template != True)

    def _apply_tool_named_filters(self, query, body: Dict[str, Any]):
        """Apply the legacy named params (search / tool_type / is_active)."""
        search = body.get("search")
        if search:
            query = query.filter(or_(
                Tool.name.ilike(f"%{search}%"),
                Tool.description.ilike(f"%{search}%"),
            ))
        tool_type = body.get("tool_type")
        if tool_type:
            query = query.filter(Tool.tool_type == tool_type)
        is_active = body.get("is_active")
        if is_active is not None:
            query = query.filter(Tool.is_active == is_active)
        return query

    def list_tools(self, body: Dict[str, Any]) -> Dict[str, Any]:
        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 20), 1), 100)
        column_map = self._tool_column_map()

        query = self._apply_tool_named_filters(self._tool_base_query(), body)
        query = apply_filters(query, body.get("filters"), column_map)

        total = query.count()

        sort_by, sort_order = resolve_sort(body, "updated_at")
        query = apply_sort(query, column_map, sort_by, sort_order, Tool.updated_at)

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return {
            "items": [self.tool_response(t) for t in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_facets(self, filters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return build_facets(
            self._tool_base_query, self._tool_column_map(), self.TOOL_FACET_FIELDS, filters
        )

    def get_filter_values(self, column_name: str) -> Dict[str, Any]:
        column_map = self._tool_column_map()
        allowed = {k: column_map[k] for k in ("name", "tool_type", "status")}
        return distinct_values(self._tool_base_query(), allowed, column_name)

    def tool_response(self, tool: Tool) -> Dict[str, Any]:
        return {
            "id": str(tool.id),
            "name": tool.name,
            "description": tool.description,
            "tool_type": tool.tool_type,
            "parameters": tool.parameters,
            "url": tool.url,
            "method": tool.method,
            "auth_type": tool.auth_type,
            "auth_config": decrypt_auth_config(tool.auth_config),
            "meta_data": tool.meta_data,
            "oauth_connection_id": tool.oauth_connection_id,
            "app_integration_id": tool.app_integration_id,
            "mcp_server_id": tool.mcp_server_id,
            "is_active": tool.is_active,
            "is_template": tool.is_template,
            "created_at": tool.created_at,
            "updated_at": tool.updated_at,
        }
