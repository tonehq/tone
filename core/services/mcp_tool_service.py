"""MCP tool integration for voice agents — connects to external MCP servers during a call.

How it works (step by step):
1. When building the pipeline, we check if the agent has any MCP servers linked.
2. If yes, for each MCP server we:
   a. Create a Pipecat MCPClient with the server URL and transport type
   b. Connect to the server and discover available tools
   c. Register tool handlers with the LLM so it can call them during the conversation
3. The discovered tools are combined with other tools (custom, document) into one list.
4. During the call, when the LLM decides to use an MCP tool, Pipecat calls the MCP server,
   gets the result, and feeds it back to the LLM.
"""

from typing import Optional

from loguru import logger

from pipecat.adapters.schemas.tools_schema import ToolsSchema


def get_mcp_servers_for_agent(agent_id: int):
    """Fetch all active MCP servers linked to an agent."""
    from core.database.session import get_db_context
    from core.models.mcp_server import McpServer
    from core.models.agent_mcp_server import AgentMcpServer

    with get_db_context() as db:
        rows = (
            db.query(McpServer)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(AgentMcpServer.agent_id == agent_id, McpServer.is_active == True)
            .all()
        )
        servers = []
        for server in rows:
            db.expunge(server)
            servers.append(server)
        return servers


async def register_mcp_tools(llm, agent_id: int) -> Optional[ToolsSchema]:
    """Connect to all MCP servers linked to an agent and register their tools with the LLM.

    Args:
        llm: The Pipecat LLM service to register tools with.
        agent_id: The agent ID to fetch MCP servers for.

    Returns:
        A ToolsSchema containing all MCP tools, or None if no MCP servers are linked.
    """
    servers = get_mcp_servers_for_agent(agent_id)
    if not servers:
        return None

    from pipecat.services.mcp_service import MCPClient
    from mcp.client.session_group import SseServerParameters, StreamableHttpParameters
    from core.services.mcp_server_service import build_auth_headers

    all_tool_schemas = []

    for server in servers:
        try:
            headers = build_auth_headers(server.auth_config)
            if server.transport_type == "sse":
                server_params = SseServerParameters(url=server.server_url, headers=headers)
            elif server.transport_type == "streamable_http":
                server_params = StreamableHttpParameters(url=server.server_url, headers=headers)
            else:
                logger.warning("Unsupported transport type '{}' for MCP server '{}', skipping", server.transport_type, server.name)
                continue

            mcp_client = MCPClient(server_params=server_params)
            tools_schema = await mcp_client.register_tools(llm)

            if tools_schema and tools_schema.standard_tools:
                all_tool_schemas.extend(tools_schema.standard_tools)
                logger.info("Registered {} MCP tools from server '{}'", len(tools_schema.standard_tools), server.name)
            else:
                logger.info("No tools found on MCP server '{}'", server.name)

        except Exception as e:
            logger.error("Failed to connect to MCP server '{}': {}", server.name, str(e))
            continue

    if all_tool_schemas:
        return ToolsSchema(standard_tools=all_tool_schemas)
    return None
