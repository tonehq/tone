import time
import uuid as uuid_lib
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.tool import Tool, AgentTool


class ToolService(BaseService):

    def create_tool(self, data: Dict[str, Any]) -> Tool:
        now = int(time.time())
        tool = Tool(
            uuid=uuid_lib.uuid4(),
            name=data["name"],
            description=data["description"],
            parameters=data.get("parameters", {}),
            url=data["url"],
            method=data.get("method", "POST"),
            auth_type=data.get("auth_type", "none"),
            auth_config=data.get("auth_config"),
            meta_data=data.get("meta_data"),
            is_active=data.get("is_active", True),
            organization_id=self.org_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def get_tools(self) -> List[Tool]:
        return self.query(Tool).all()

    def get_tool(self, tool_id: int) -> Tool:
        tool = self.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found",
            )
        return tool

    def update_tool(self, tool_id: int, data: Dict[str, Any]) -> Tool:
        tool = self.get_tool(tool_id)
        for key, value in data.items():
            if hasattr(tool, key):
                setattr(tool, key, value)
        tool.updated_at = int(time.time())
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def delete_tool(self, tool_id: int) -> Dict[str, str]:
        tool = self.get_tool(tool_id)
        self.db.delete(tool)
        self.db.commit()
        return {"message": "Tool deleted successfully"}

    def attach_tool_to_agents(self, agent_ids: List[int], tool_id: int) -> List[AgentTool]:
        # Verify tool exists
        self.get_tool(tool_id)

        # Check which are already attached
        existing = (
            self.db.query(AgentTool.agent_id)
            .filter(AgentTool.tool_id == tool_id, AgentTool.agent_id.in_(agent_ids))
            .all()
        )
        existing_ids = {row[0] for row in existing}
        new_ids = [aid for aid in agent_ids if aid not in existing_ids]

        if not new_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tool is already attached to all specified agents",
            )

        now = int(time.time())
        agent_tools = []
        for agent_id in new_ids:
            agent_tool = AgentTool(
                agent_id=agent_id,
                tool_id=tool_id,
                created_at=now,
                updated_at=now,
            )
            agent_tools.append(agent_tool)
        self.db.add_all(agent_tools)
        self.db.commit()
        return agent_tools

    def detach_tool_from_agents(self, agent_ids: List[int], tool_id: int) -> Dict[str, str]:
        agent_tools = (
            self.db.query(AgentTool)
            .filter(AgentTool.tool_id == tool_id, AgentTool.agent_id.in_(agent_ids))
            .all()
        )
        if not agent_tools:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool is not attached to any of the specified agents",
            )
        for at in agent_tools:
            self.db.delete(at)
        self.db.commit()
        return {"message": f"Tool detached from {len(agent_tools)} agent(s) successfully"}

    def get_tools_by_agent(self, agent_id: int) -> List[Tool]:
        return (
            self.query(Tool)
            .join(AgentTool, AgentTool.tool_id == Tool.id)
            .filter(AgentTool.agent_id == agent_id, Tool.is_active == True)
            .all()
        )

    def tool_response(self, tool: Tool) -> Dict[str, Any]:
        return {
            "id": tool.id,
            "uuid": str(tool.uuid),
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "url": tool.url,
            "method": tool.method,
            "auth_type": tool.auth_type,
            "auth_config": tool.auth_config,
            "meta_data": tool.meta_data,
            "is_active": tool.is_active,
            "created_at": tool.created_at,
            "updated_at": tool.updated_at,
        }
