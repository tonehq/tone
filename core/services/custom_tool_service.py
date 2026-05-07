"""Custom tool service for voice agents — lets the LLM call customer-defined webhook tools and built-in tools during a call."""

import json
from typing import Any, Callable, List, Optional

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


def create_built_in_tool_handler(tool: Tool, caller_number: str) -> Callable:
    """Create a handler for a built-in tool (e.g. send_sms)."""

    if tool.name == "send_sms":
        return _create_send_sms_handler(tool, caller_number)

    # Fallback: unknown built-in tool
    async def noop_handler(params: FunctionCallParams) -> None:
        logger.warning("Unknown built-in tool '{}' called", tool.name)
        await params.result_callback(f"Unknown built-in tool: {tool.name}")

    return noop_handler


def _create_send_sms_handler(tool: Tool, caller_number: str) -> Callable:
    """Create a handler that sends an SMS via Twilio."""

    async def handle_send_sms(params: FunctionCallParams) -> None:
        arguments = params.arguments
        message = arguments.get("message", "")
        logger.info("Built-in tool 'send_sms' called. Sending SMS to {}", caller_number)

        meta = tool.meta_data or {}
        account_sid = meta.get("account_sid")
        auth_token = meta.get("auth_token")
        from_number = meta.get("from_number")

        if not all([account_sid, auth_token, from_number]):
            logger.error("send_sms tool missing Twilio credentials in meta_data")
            await params.result_callback("Error: SMS tool is not configured. Missing Twilio credentials.")
            return

        if not caller_number:
            logger.error("send_sms tool: no caller phone number available")
            await params.result_callback("Error: Caller phone number is not available for this call.")
            return

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    auth=(account_sid, auth_token),
                    data={
                        "From": from_number,
                        "To": caller_number,
                        "Body": message,
                    },
                )

            if response.status_code == 201:
                logger.info("SMS sent successfully to {}", caller_number)
                await params.result_callback("SMS sent successfully.")
            else:
                error_detail = response.text
                logger.error("SMS sending failed: status={} body={}", response.status_code, error_detail)
                await params.result_callback(f"Failed to send SMS: {error_detail}")

        except Exception as e:
            logger.error("send_sms tool failed: {}", e)
            await params.result_callback(f"Error sending SMS: {str(e)}")

    return handle_send_sms
