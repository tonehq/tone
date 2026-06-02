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

import asyncio
import time
from typing import Optional

from loguru import logger

from pipecat.adapters.schemas.tools_schema import ToolsSchema

from core.utils.logging import truncate_for_log

# Hard ceiling on how long discovering tools from a single MCP server may take at
# pipeline-build time. A dead or mis-authenticated server must fail fast and
# visibly rather than silently yielding zero tools (or blocking call setup).
MCP_REGISTER_TIMEOUT_S = 25.0


def _install_mcp_call_logging(llm, server_name: str, tool_call_entries=None, current_turn=None):
    """Wrap ``llm.register_function`` so each MCP tool registered through it logs, at call time,
    its server + tool name, the arguments passed in, and the output returned (plus duration) —
    and, when ``tool_call_entries`` is provided, appends a structured entry so the invocation is
    persisted to the ``tool_executions`` table alongside custom/built-in tool calls.

    Pipecat's ``MCPClient.register_tools`` registers its handlers via ``llm.register_function``;
    by shadowing that method on the instance for the duration of registration we transparently
    decorate every MCP handler with logging without touching Pipecat internals.

    Returns a zero-arg callable that restores the original ``register_function``.
    """
    original_register = llm.register_function

    def logging_register(name, handler, *args, **kwargs):
        async def logged_handler(params):
            fn = getattr(params, "function_name", name)
            arguments = getattr(params, "arguments", {})
            started = time.monotonic()
            logger.info(
                "🔧 MCP tool call → server='{}' tool='{}' args={}",
                server_name, fn, truncate_for_log(arguments),
            )

            # One entry per invocation, mirroring the custom/built-in tool shape so
            # ToolExecutionService can map it uniformly.
            entry = {
                "tool": fn,
                "tool_type": "mcp",
                "server": server_name,
                "arguments": arguments,
                "timestamp": int(time.time()),
                "turn": current_turn["number"] if current_turn else None,
            }

            original_cb = getattr(params, "result_callback", None)
            if original_cb is not None:
                async def logging_cb(result, *cb_args, **cb_kwargs):
                    dur = round((time.monotonic() - started) * 1000)
                    logger.info(
                        "✅ MCP tool result ← server='{}' tool='{}' ({}ms) output={}",
                        server_name, fn, dur, truncate_for_log(result),
                    )
                    if tool_call_entries is not None:
                        entry["result"] = result
                        entry["status"] = "success"
                        entry["duration_ms"] = dur
                        tool_call_entries.append(entry)
                    return await original_cb(result, *cb_args, **cb_kwargs)

                try:
                    params.result_callback = logging_cb
                except Exception:
                    # FunctionCallParams not mutable on this version — still log the call above.
                    pass

            try:
                return await handler(params)
            except Exception as exc:
                dur = round((time.monotonic() - started) * 1000)
                logger.error(
                    "❌ MCP tool error ✕ server='{}' tool='{}' ({}ms): {}",
                    server_name, fn, dur, exc,
                )
                if tool_call_entries is not None:
                    entry["status"] = "error"
                    entry["error"] = str(exc)
                    entry["duration_ms"] = dur
                    tool_call_entries.append(entry)
                raise

        return original_register(name, logged_handler, *args, **kwargs)

    llm.register_function = logging_register
    return lambda: setattr(llm, "register_function", original_register)


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


async def register_mcp_tools(llm, agent_id: int, tool_call_entries=None, current_turn=None) -> Optional[ToolsSchema]:
    """Connect to all MCP servers linked to an agent and register their tools with the LLM.

    Args:
        llm: The Pipecat LLM service to register tools with.
        agent_id: The agent ID to fetch MCP servers for.
        tool_call_entries: Optional shared list each MCP invocation is appended to,
            so it's persisted to the tool_executions table at call completion.
        current_turn: Optional dict carrying the live conversation turn number.

    Returns:
        A ToolsSchema containing all MCP tools, or None if no MCP servers are linked.
    """
    servers = get_mcp_servers_for_agent(agent_id)
    if not servers:
        logger.info("Agent {} has no active linked MCP servers; no MCP tools registered", agent_id)
        return None

    logger.info("Agent {} has {} active MCP server(s); registering tools", agent_id, len(servers))

    from pipecat.services.mcp_service import MCPClient
    from mcp.client.session_group import SseServerParameters, StreamableHttpParameters
    from core.services.mcp_server_service import build_auth_headers, headers_from_meta

    all_tool_schemas = []

    for server in servers:
        try:
            # Header precedence mirrors validate_mcp_connection exactly: static auth_config first,
            # then custom meta_data headers (e.g. ClickUp's x-workspace-id) override those, then the
            # OAuth bearer (resolved below) overrides everything. Keeping the order identical here
            # ensures a server that validates with one set of headers authenticates with the same
            # set during a live call.
            headers = build_auth_headers(server.auth_config)
            headers.update(headers_from_meta(getattr(server, "meta_data", None)))

            # OAuth-backed connectors (e.g. ClickUp, Google Calendar) authenticate via a
            # linked OAuth connection, NOT a static header. Resolve a fresh (auto-refreshed)
            # bearer token so their tools actually load — without this the remote returns
            # 0 tools (or 401) and the agent silently can't book anything.
            oauth_connection_id = getattr(server, "oauth_connection_id", None)
            if oauth_connection_id:
                try:
                    from core.database.session import get_db_context
                    from core.services.oauth_service import OAuthService

                    with get_db_context() as db:
                        svc = OAuthService(db, org_id=server.organization_id)
                        connection = svc.get_connection(oauth_connection_id)
                        if connection:
                            # Non-blocking scope check: surface a clear warning if the granted
                            # scopes don't cover what the provider needs, so a partially-authorized
                            # connection doesn't quietly expose a subset of tools.
                            scope_check = svc.validate_connection_for_provider(connection)
                            if not scope_check["ok"]:
                                logger.warning(
                                    "MCP server '{}' OAuth connection {} is missing scopes {} — "
                                    "some tools may be unavailable; reconnect to grant them",
                                    server.name, oauth_connection_id, scope_check["missing"],
                                )
                            token = svc.get_valid_access_token_for_connection(connection)
                            headers["Authorization"] = f"Bearer {token}"
                            logger.info(
                                "MCP server '{}' authenticated via OAuth connection {}",
                                server.name, oauth_connection_id,
                            )
                        else:
                            logger.warning(
                                "MCP server '{}' references missing OAuth connection {} — "
                                "reconnect it in Integrations settings",
                                server.name, oauth_connection_id,
                            )
                except Exception as e:
                    logger.error(
                        "MCP server '{}': failed to resolve OAuth access token: {}",
                        server.name, str(e),
                    )

            if not headers:
                # Surfaces the most common silent failure: a server that requires auth
                # but whose credential isn't materialised into a request header, so the
                # remote returns 0 tools (or 401) and booking silently no-ops.
                logger.warning(
                    "MCP server '{}' resolved NO auth headers — if it requires auth, "
                    "tool discovery will return nothing. Check its auth_config / OAuth connection.",
                    server.name,
                )
            if server.transport_type == "sse":
                server_params = SseServerParameters(url=server.server_url, headers=headers)
            elif server.transport_type == "streamable_http":
                server_params = StreamableHttpParameters(url=server.server_url, headers=headers)
            else:
                logger.warning("Unsupported transport type '{}' for MCP server '{}', skipping", server.transport_type, server.name)
                continue

            logger.info(
                "Connecting to MCP server '{}' ({}, {} auth header(s))",
                server.name, server.transport_type, len(headers),
            )
            mcp_client = MCPClient(server_params=server_params)
            # Decorate every handler MCPClient registers so MCP tool calls log their
            # name/arguments/output during the conversation; restore afterwards so only this
            # server's tools are wrapped.
            restore_logging = _install_mcp_call_logging(
                llm, server.name, tool_call_entries=tool_call_entries, current_turn=current_turn
            )
            try:
                tools_schema = await asyncio.wait_for(
                    mcp_client.register_tools(llm), timeout=MCP_REGISTER_TIMEOUT_S
                )
            finally:
                restore_logging()

            if tools_schema and tools_schema.standard_tools:
                tool_names = [getattr(t, "name", "?") for t in tools_schema.standard_tools]
                all_tool_schemas.extend(tools_schema.standard_tools)
                logger.info(
                    "Registered {} MCP tools from server '{}': {}",
                    len(tools_schema.standard_tools), server.name, tool_names,
                )
            else:
                logger.warning(
                    "MCP server '{}' connected but exposed NO tools — the agent will not "
                    "be able to act on it (e.g. create ClickUp task / calendar event)",
                    server.name,
                )

        except asyncio.TimeoutError:
            logger.error(
                "Timed out after {}s discovering tools from MCP server '{}' ({})",
                MCP_REGISTER_TIMEOUT_S, server.name, server.server_url,
            )
            continue
        except Exception as e:
            logger.error("Failed to connect to MCP server '{}': {}", server.name, str(e))
            continue

    if all_tool_schemas:
        return ToolsSchema(standard_tools=all_tool_schemas)
    return None
