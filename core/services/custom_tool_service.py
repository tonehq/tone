"""Custom tool service for voice agents — lets the LLM call customer-defined webhook tools during a call."""

import json
from typing import Any, List, Optional

import httpx
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from core.models.tool import Tool, AgentTool


def get_custom_tools_for_agent(agent_id: int) -> List[Tool]:
    """Fetch all active custom tools linked to an agent."""
    from core.database.session import get_db_context

    with get_db_context() as db:
        tools = (
            db.query(Tool)
            .join(AgentTool, AgentTool.tool_id == Tool.id)
            .filter(AgentTool.agent_id == agent_id, Tool.is_active == True)
            .all()
        )
        # Detach from session so they can be used after db closes
        for tool in tools:
            db.expunge(tool)

    logger.info("Found {} custom tools for agent {}", len(tools), agent_id)
    return tools


def build_custom_tool_schemas(tools: List[Tool]) -> Optional[ToolsSchema]:
    """Convert Tool DB records into Pipecat ToolsSchema for LLMContext."""
    if not tools:
        return None

    function_schemas = []
    for tool in tools:
        params = tool.parameters or {}
        properties = params.get("properties", {})
        required = params.get("required", [])

        schema = FunctionSchema(
            name=tool.name,
            description=tool.description,
            properties=properties,
            required=required,
        )
        function_schemas.append(schema)
        logger.info("Built schema for custom tool: {}", tool.name)

    return ToolsSchema(standard_tools=function_schemas)


def create_custom_tool_handler(tool: Tool):
    """Create a handler function for a custom tool that calls the customer's webhook."""

    async def handle_tool_call(params: FunctionCallParams) -> None:
        arguments = params.arguments
        logger.info("Custom tool '{}' called with args: {}", tool.name, arguments)

        try:
            # Build request headers
            headers = {"Content-Type": "application/json"}

            # Add auth headers based on auth_type
            auth_config = tool.auth_config or {}
            logger.info("Custom tool '{}' auth_type={} auth_config={}", tool.name, tool.auth_type, auth_config)
            if tool.auth_type == "api_key":
                header_name = auth_config.get("header", "X-API-Key")
                headers[header_name] = auth_config.get("value", "")
            elif tool.auth_type == "bearer_token" or tool.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
            elif tool.auth_type == "basic" or tool.auth_type == "basic_auth" :
                import base64
                username = auth_config.get("username", "")
                password = auth_config.get("password", "")
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

            # Build the URL — replace {placeholder} with argument values
            url = tool.url
            remaining_args = dict(arguments)
            for key, value in arguments.items():
                placeholder = "{" + key + "}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
                    remaining_args.pop(key)

            # Make HTTP request to the customer's webhook
            async with httpx.AsyncClient(timeout=30.0) as client:
                if tool.method.upper() == "GET":
                    response = await client.get(url, params=remaining_args, headers=headers)
                else:
                    response = await client.request(
                        method=tool.method.upper(),
                        url=url,
                        json=remaining_args,
                        headers=headers,
                    )

            # Parse and return the response
            try:
                result = response.json()
                result_text = json.dumps(result)
            except Exception:
                result_text = response.text

            logger.info("Custom tool '{}' returned status {}", tool.name, response.status_code)
            await params.result_callback(result_text)

        except Exception as e:
            logger.error("Custom tool '{}' failed: {}", tool.name, e)
            await params.result_callback(f"Error calling tool: {str(e)}")

    return handle_tool_call
