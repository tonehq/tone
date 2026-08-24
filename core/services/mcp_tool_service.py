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

from core.services.pipeline.tool_call_timing import (
    ToolCallTimer,
    finalize_and_record,
)
from core.utils.logging import truncate_for_log
from core.utils.tool_idempotency import booking_signature, is_cacheable_result

# Hard ceiling on how long discovering tools from a single MCP server may take at
# pipeline-build time. A dead or mis-authenticated server must fail fast and
# visibly rather than silently yielding zero tools (or blocking call setup).
MCP_REGISTER_TIMEOUT_S = 60.0


def _install_mcp_call_logging(llm, server_name: str, server_id=None, tool_call_entries=None, tool_request_ts=None, current_turn=None, tool_dedup=None):
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
            timer = ToolCallTimer.start(params, tool_request_ts)
            logger.bind(
                tool_name=fn,
                tool_type="mcp",
                mcp_server_id=str(server_id) if server_id else None,
                mcp_server_name=server_name,
            ).info(
                "[mcp-tool] tool call server='{}' tool='{}' args={}",
                server_name, fn, truncate_for_log(arguments),
            )

            # One entry per invocation, mirroring the custom/built-in tool shape so
            # ToolExecutionService can map it uniformly. Recorded UP FRONT (status
            # "started") and appended now so the call is persisted even if its
            # result is never delivered — e.g. a barge-in interruption discards it
            # ("tool_call_id is not running") or it completes after call shutdown.
            # The same dict is updated in place on result/error; timer.finish stamps
            # completed_at without re-appending (entry is already in the sink).
            entry = {
                "tool": fn,
                "tool_type": "mcp",
                "server": server_name,
                "mcp_server_id": str(server_id) if server_id else None,
                "arguments": arguments,
                "timestamp": int(time.time()),
                "turn": current_turn["number"] if current_turn else None,
                "status": "started",
                **timer.initial_fields(),
            }
            if tool_call_entries is not None:
                tool_call_entries.append(entry)

            original_cb = getattr(params, "result_callback", None)

            # In-call idempotency: if this exact create-type call already succeeded
            # this call (e.g. a barge-in discarded the first result and the LLM
            # re-issued the booking), return the cached result instead of creating
            # a duplicate ClickUp task.
            sig = booking_signature(fn, arguments) if tool_dedup is not None else None
            if sig is not None and sig in tool_dedup:
                cached = tool_dedup[sig]
                dur = round((time.monotonic() - started) * 1000)
                logger.bind(
                    tool_name=fn,
                    tool_type="mcp",
                    mcp_server_id=str(server_id) if server_id else None,
                    mcp_server_name=server_name,
                ).warning(
                    "[mcp-tool] duplicate call suppressed server='{}' tool='{}' "
                    "— returning cached result",
                    server_name, fn,
                )
                entry["result"] = cached
                entry["status"] = "duplicate_suppressed"
                entry["status_code"] = 200
                entry["duration_ms"] = dur
                finalize_and_record(entry, timer, None)
                if original_cb is not None:
                    await original_cb(cached)
                return

            if original_cb is not None:
                async def logging_cb(result, *cb_args, **cb_kwargs):
                    dur = round((time.monotonic() - started) * 1000)
                    logger.bind(
                        tool_name=fn,
                        tool_type="mcp",
                        mcp_server_id=str(server_id) if server_id else None,
                        mcp_server_name=server_name,
                        elapsed_ms=dur,
                    ).info(
                        "[mcp-tool] result server='{}' tool='{}' ({}ms) output={}",
                        server_name, fn, dur, truncate_for_log(result),
                    )
                    entry["result"] = result
                    entry["status"] = "success"
                    entry["status_code"] = 200
                    entry["duration_ms"] = dur
                    finalize_and_record(entry, timer, None)
                    if sig is not None and tool_dedup is not None and is_cacheable_result(result):
                        tool_dedup[sig] = result
                    return await original_cb(result, *cb_args, **cb_kwargs)

                try:
                    params.result_callback = logging_cb
                except Exception as exc:
                    # FunctionCallParams not mutable on this version — still log the call above.
                    logger.debug("FunctionCallParams.result_callback not mutable: {}", exc)
                    pass

            try:
                return await handler(params)
            except Exception as exc:
                dur = round((time.monotonic() - started) * 1000)
                logger.bind(
                    tool_name=fn,
                    tool_type="mcp",
                    mcp_server_id=str(server_id) if server_id else None,
                    mcp_server_name=server_name,
                    elapsed_ms=dur,
                ).exception(
                    "[mcp-tool] error server='{}' tool='{}' ({}ms)",
                    server_name, fn, dur,
                )
                entry["status"] = "error"
                entry["error"] = str(exc)
                entry["status_code"] = 500
                entry["duration_ms"] = dur
                finalize_and_record(entry, timer, None)
                raise

        return original_register(name, logged_handler, *args, **kwargs)

    llm.register_function = logging_register
    return lambda: setattr(llm, "register_function", original_register)


def get_mcp_servers_for_agent(agent_id: int):
    """Fetch all active MCP servers linked to an agent's published version.

    The link table's ``oauth_connection_id`` (per-version override) is selected
    in the same query and stamped onto each ``McpServer`` as
    ``effective_oauth_connection_id`` — the OAuth header builder reads that
    attribute so the override rule stays in one place.
    """
    from core.database.session import get_db_context
    from core.models.mcp_server import McpServer
    from core.models.agent_mcp_server import AgentMcpServer
    from core.utils.agent_scope import published_config_subquery
    from core.utils.oauth_resolution import stamp_effective

    published_config_sq = published_config_subquery(agent_id)

    with get_db_context() as db:
        rows = (
            db.query(McpServer, AgentMcpServer.oauth_connection_id)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(
                AgentMcpServer.agent_id == agent_id,
                AgentMcpServer.agent_config_id == published_config_sq,
                McpServer.is_active == True,
            )
            .all()
        )
        servers = []
        for server, link_oauth in rows:
            stamp_effective(server, link_oauth)
            db.expunge(server)
            servers.append(server)
        return servers


def build_mcp_request_headers(server) -> dict:
    from core.services.mcp_server_service import build_auth_headers, headers_from_meta
    from core.utils.oauth_resolution import effective_of

    headers = build_auth_headers(
        server.auth_config, auth_type=getattr(server, "auth_type", None)
    )
    headers.update(headers_from_meta(getattr(server, "meta_data", None)))

    oauth_connection_id = effective_of(server)
    if oauth_connection_id:
        try:
            from core.database.session import get_db_context
            from core.services.oauth_service import OAuthService

            with get_db_context() as db:
                svc = OAuthService(db, org_id=server.organization_id)
                connection = svc.get_connection(oauth_connection_id)
                if connection:
                    scope_check = svc.validate_connection_for_provider(connection)
                    if not scope_check["ok"]:
                        logger.warning(
                            "MCP server '{}' OAuth connection {} is missing scopes {} — "
                            "some tools may be unavailable; reconnect to grant them",
                            server.name, oauth_connection_id, scope_check["missing"],
                        )
                    header_name, header_value = svc.resolve_connection_auth_header(connection)
                    headers[header_name] = header_value
                    logger.info(
                        "MCP server '{}' authenticated via connection {}",
                        server.name, oauth_connection_id,
                    )
                else:
                    logger.warning(
                        "MCP server '{}' references missing OAuth connection {} — "
                        "reconnect it in Integrations settings",
                        server.name, oauth_connection_id,
                    )
        except Exception:
            logger.exception(
                "MCP server '{}': failed to resolve OAuth access token", server.name
            )

    if not headers:
        logger.warning(
            "MCP server '{}' resolved NO auth headers — if it requires auth, "
            "tool discovery will return nothing. Check its auth_config / OAuth connection.",
            server.name,
        )
    return headers


def get_mcp_server_refs(agent_id: int) -> list:
    """`[{id, name}, ...]` for the agent's active MCP servers.

    Cached alongside the rest of the pipeline payload so the call-log snapshot can
    record which MCP servers were wired in without a per-call DB hit. Independent of
    `get_mcp_servers_for_agent` (which returns full ORM rows the builder needs to
    connect to each server live).
    """
    from core.database.session import get_db_context
    from core.models.mcp_server import McpServer
    from core.models.agent_mcp_server import AgentMcpServer
    from core.utils.agent_scope import published_config_subquery

    published_config_sq = published_config_subquery(agent_id)

    with get_db_context() as db:
        rows = (
            db.query(McpServer.id, McpServer.name)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(
                AgentMcpServer.agent_id == agent_id,
                AgentMcpServer.agent_config_id == published_config_sq,
                McpServer.is_active.is_(True),
            )
            .all()
        )
    return [{"id": str(r.id), "name": r.name} for r in rows]


def _collect_json_refs(obj, out: list) -> None:
    """Recursively walk a JSON value, appending every ``$ref`` string to ``out``."""
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if isinstance(ref, str):
            out.append(ref)
        for v in obj.values():
            _collect_json_refs(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_json_refs(item, out)


def _json_ref_resolves(ref: str, schema_root: dict) -> bool:
    """Return True iff ``ref`` is a local JSON Pointer (``#/...``) that resolves
    against ``schema_root``. External or dangling references return False."""
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return False
    cur = schema_root
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and token in cur:
            cur = cur[token]
        elif isinstance(cur, list):
            try:
                cur = cur[int(token)]
            except (ValueError, IndexError):
                return False
        else:
            return False
    return True


def _schema_has_unresolved_refs(schema) -> tuple:
    """Return ``(has_bad, list_of_bad_refs)`` for a JSON schema.

    Some MCP servers (notably HubSpot's ``manage_crm_objects``) ship tool schemas
    whose ``$ref`` pointers target definitions that were never included. Strict
    LLM APIs (Groq, Gemini) reject the entire tool batch when any one schema is
    malformed — killing every other tool on the same agent. We pre-validate so
    the broken tools can be dropped while the rest continue to work.
    """
    if not isinstance(schema, dict) or not schema:
        return False, []
    refs: list = []
    _collect_json_refs(schema, refs)
    if not refs:
        return False, []
    unresolved = [r for r in refs if not _json_ref_resolves(r, schema)]
    return bool(unresolved), unresolved


_MAX_INLINE_DEPTH = 24
_MAX_SCHEMA_BYTES = 60000
_UNSUPPORTED_KEYS = ("$schema", "$id", "$defs", "definitions")


def _resolve_pointer(ref: str, root: dict):
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None
    cur = root
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and token in cur:
            cur = cur[token]
        elif isinstance(cur, list):
            try:
                cur = cur[int(token)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def sanitize_json_schema(schema, root=None, depth=0, seen=None, budget=None):
    if root is None:
        root = schema if isinstance(schema, dict) else {}
    if seen is None:
        seen = set()
    if budget is None:
        budget = {"bytes": 0, "truncated": 0}

    if isinstance(schema, list):
        return [sanitize_json_schema(v, root, depth + 1, seen, budget) for v in schema]
    if not isinstance(schema, dict):
        budget["bytes"] += 8
        return schema
    if depth > _MAX_INLINE_DEPTH or budget["bytes"] > _MAX_SCHEMA_BYTES:
        budget["truncated"] += 1
        return {"type": "object"}

    ref = schema.get("$ref")
    if isinstance(ref, str):
        if ref in seen:
            return {"type": "object"}
        target = _resolve_pointer(ref, root)
        if not isinstance(target, dict):
            return {"type": "object"}
        merged = {k: v for k, v in schema.items() if k != "$ref"}
        merged = {**target, **merged}
        return sanitize_json_schema(merged, root, depth + 1, seen | {ref}, budget)

    out = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED_KEYS:
            continue
        budget["bytes"] += len(key) + 4
        if key == "const":
            out["enum"] = [value]
            continue
        out[key] = sanitize_json_schema(value, root, depth + 1, seen, budget)
    return out


def install_schema_sanitizer(mcp_client) -> None:
    original = getattr(mcp_client, "_convert_mcp_schema_to_pipecat", None)
    if original is None:
        logger.debug("MCPClient has no _convert_mcp_schema_to_pipecat; skipping sanitizer")
        return

    def converting(tool_name, tool_schema, *args, **kwargs):
        try:
            raw = (tool_schema or {}).get("input_schema") or {}
            budget = {"bytes": 0, "truncated": 0}
            cleaned = sanitize_json_schema(raw, budget=budget)
            if budget["truncated"]:
                logger.warning(
                    "MCP tool '{}': {} schema branch(es) collapsed to a generic object "
                    "(depth>{} or size>{}B) — the model loses those parameter shapes",
                    tool_name, budget["truncated"], _MAX_INLINE_DEPTH, _MAX_SCHEMA_BYTES,
                )
            if cleaned != raw:
                tool_schema = {**tool_schema, "input_schema": cleaned}
                logger.debug("Sanitized schema for MCP tool '{}'", tool_name)
        except Exception:
            logger.exception("Schema sanitize failed for MCP tool '{}'; using original", tool_name)
        return original(tool_name, tool_schema, *args, **kwargs)

    mcp_client._convert_mcp_schema_to_pipecat = converting


async def _filter_invalid_mcp_tool_schemas(mcp_client) -> tuple:
    """Pre-list the MCP server's tools, validate their JSON schemas, and configure
    ``mcp_client``'s built-in ``tools_filter`` to skip ones with unresolved $refs.

    Returns ``(kept_names_or_None, dropped_with_reasons)``. On any internal
    error (e.g. pipecat changed its private API) returns ``(None, [])`` so
    registration falls back to no filtering — never blocks tool loading.

    Cost: one extra ``session.list_tools()`` round-trip per server at pipeline
    build time (~50–150 ms). Zero overhead during the live call.
    """
    try:
        session = mcp_client._ensure_connected()
        available = await session.list_tools()
    except Exception as e:
        logger.debug("Schema pre-validation skipped (could not list tools): {}", e)
        return None, []

    kept: set = set()
    dropped: list = []
    for tool in getattr(available, "tools", []) or []:
        try:
            has_bad, bad_refs = _schema_has_unresolved_refs(tool.inputSchema or {})
        except Exception as exc:
            logger.debug("Schema validation skipped for MCP tool '{}': {}", tool.name, exc)
            kept.add(tool.name)
            continue
        if has_bad:
            dropped.append((tool.name, bad_refs[:2]))
        else:
            kept.add(tool.name)

    if dropped:
        try:
            mcp_client._tools_filter = kept
        except Exception:
            logger.exception(
                "Could not apply tools_filter to MCPClient (pipecat API may have changed)",
            )
            return None, dropped

    return kept, dropped


async def register_mcp_tools(llm, agent_id: int, tool_call_entries=None, tool_request_ts=None, current_turn=None, tool_dedup=None) -> Optional[ToolsSchema]:
    """Connect to all MCP servers linked to an agent and register their tools with the LLM.

    Args:
        llm: The Pipecat LLM service to register tools with.
        agent_id: The agent ID to fetch MCP servers for.
        tool_call_entries: Optional shared list each MCP invocation is appended to,
            so it's persisted to the tool_executions table at call completion.
        tool_request_ts: Optional runner-owned ``{tool_call_id: llm_requested_at}``
            map, populated by LlmRequestStamper's register_function wrapper on
            handler dispatch.
        current_turn: Optional dict carrying the live conversation turn number.
        tool_dedup: Optional shared dict (per-call) used to suppress duplicate
            create-type tool calls (e.g. clickup_create_task fired twice).

    Returns:
        A ToolsSchema containing all MCP tools, or None if no MCP servers are linked.
    """
    _t_start = time.monotonic()
    servers = get_mcp_servers_for_agent(agent_id)
    # Shadow the module-level logger for the whole call so every line — including
    # nested ``.bind()``/``.exception()`` blocks inside the per-server loop —
    # automatically carries ``agent_id`` and (when at least one server exists)
    # ``organization_id`` for multi-tenant Grafana / Loki filtering.
    _org_id = getattr(servers[0], "organization_id", None) if servers else None
    logger = globals()["logger"].bind(agent_id=agent_id, organization_id=_org_id)

    if not servers:
        logger.info(
            "[mcp-tool] agent {} has no active linked MCP servers — no MCP tools registered",
            agent_id,
        )
        return None

    logger.bind(server_count=len(servers)).info(
        "[mcp-tool] agent {} has {} active MCP server(s) — registering tools",
        agent_id, len(servers),
    )
    succeeded_count = 0
    failed_count = 0

    from pipecat.services.mcp_service import MCPClient
    from mcp.client.session_group import SseServerParameters, StreamableHttpParameters
    from core.services.mcp_server_service import resolve_server_url

    all_tool_schemas = []

    for server in servers:
        try:
            headers = build_mcp_request_headers(server)
            connect_url = resolve_server_url(server)
            if server.transport_type == "sse":
                server_params = SseServerParameters(url=connect_url, headers=headers)
            elif server.transport_type == "streamable_http":
                server_params = StreamableHttpParameters(url=connect_url, headers=headers)
            else:
                logger.bind(
                    agent_id=agent_id,
                    mcp_server_id=str(server.id) if server.id else None,
                    mcp_server_name=server.name,
                    transport_type=server.transport_type,
                ).warning(
                    "[mcp-tool] unsupported transport type '{}' for MCP server '{}' — skipping",
                    server.transport_type, server.name,
                )
                continue

            logger.bind(
                agent_id=agent_id,
                mcp_server_id=str(server.id) if server.id else None,
                mcp_server_name=server.name,
                transport_type=server.transport_type,
                auth_header_count=len(headers),
            ).info(
                "[mcp-tool] connecting to MCP server '{}' ({}, {} auth header(s))",
                server.name, server.transport_type, len(headers),
            )
            mcp_client = MCPClient(server_params=server_params)
            install_schema_sanitizer(mcp_client)
            # Pipecat's newer MCPClient requires an explicit start() (or `async with`) before
            # register_tools / tool calls — without it `_ensure_connected` raises
            # "MCPClient is not connected". We use start() (not `async with`) because the
            # session must stay open for the entire call: the LLM keeps a reference to
            # mcp_client._tool_wrapper, which uses the same session at runtime.
            await asyncio.wait_for(mcp_client.start(), timeout=MCP_REGISTER_TIMEOUT_S)

            # Pre-validate tool schemas: some MCP servers (HubSpot's ``manage_crm_objects``,
            # for example) advertise tools whose JSON schemas contain unresolved ``$ref``s.
            # Strict LLM APIs reject the entire tool batch when any one schema is malformed,
            # so without this step a single bad tool silently breaks every other tool on the
            # same agent. We configure the MCPClient's built-in ``tools_filter`` so the
            # downstream ``register_tools`` skips the broken ones automatically.
            try:
                _kept, _dropped = await asyncio.wait_for(
                    _filter_invalid_mcp_tool_schemas(mcp_client),
                    timeout=MCP_REGISTER_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                logger.bind(
                    agent_id=agent_id,
                    mcp_server_id=str(server.id) if server.id else None,
                    mcp_server_name=server.name,
                    timeout_seconds=MCP_REGISTER_TIMEOUT_S,
                ).warning(
                    "[mcp-tool] schema pre-validation timed out for MCP server '{}' — "
                    "continuing without filtering",
                    server.name,
                )
                _kept, _dropped = None, []
            if _dropped:
                logger.bind(
                    agent_id=agent_id,
                    mcp_server_id=str(server.id) if server.id else None,
                    mcp_server_name=server.name,
                    dropped_count=len(_dropped),
                ).warning(
                    "[mcp-tool] MCP server '{}' dropped {} tool(s) with invalid JSON schemas: {}",
                    server.name, len(_dropped),
                    [name for name, _ in _dropped],
                )
                for _name, _refs in _dropped:
                    logger.debug(
                        "MCP server '{}': tool '{}' has unresolved $refs: {}",
                        server.name, _name, _refs,
                    )

            # Decorate every handler MCPClient registers so MCP tool calls log their
            # name/arguments/output during the conversation; restore afterwards so only this
            # server's tools are wrapped.
            restore_logging = _install_mcp_call_logging(
                llm, server.name, server_id=server.id,
                tool_call_entries=tool_call_entries,
                tool_request_ts=tool_request_ts,
                current_turn=current_turn, tool_dedup=tool_dedup,
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
                succeeded_count += 1
                logger.bind(
                    mcp_server_id=str(server.id) if server.id else None,
                    mcp_server_name=server.name,
                    tool_count=len(tools_schema.standard_tools),
                ).info(
                    "[mcp-tool] registered {} MCP tools from server '{}': {}",
                    len(tools_schema.standard_tools), server.name, tool_names,
                )
            else:
                # Connected but zero tools — surfaced but NOT counted as a
                # failure (the server responded; it just had nothing useful).
                succeeded_count += 1
                logger.bind(
                    mcp_server_id=str(server.id) if server.id else None,
                    mcp_server_name=server.name,
                ).warning(
                    "[mcp-tool] MCP server '{}' connected but exposed NO tools — the agent "
                    "will not be able to act on it (e.g. create ClickUp task / calendar event)",
                    server.name,
                )

        except asyncio.TimeoutError:
            # Use ``.exception`` (not ``.error``) so the full traceback lands
            # in Loki — matches the project-wide rule that every ``except``
            # captures a stack, not just a message. See CLAUDE.md logging rules.
            failed_count += 1
            logger.bind(
                mcp_server_id=str(server.id) if server.id else None,
                mcp_server_name=server.name,
                timeout_seconds=MCP_REGISTER_TIMEOUT_S,
            ).exception(
                "[mcp-tool] timed out after {}s discovering tools from MCP server '{}' ({})",
                MCP_REGISTER_TIMEOUT_S, server.name, server.server_url,
            )
            continue
        except Exception:
            failed_count += 1
            logger.bind(
                mcp_server_id=str(server.id) if server.id else None,
                mcp_server_name=server.name,
                server_url=server.server_url,
            ).exception(
                "[mcp-tool] failed to connect to MCP server '{}'", server.name
            )
            continue

    _elapsed_ms = int((time.monotonic() - _t_start) * 1000)
    logger.bind(
        server_count=len(servers),
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        total_tool_count=len(all_tool_schemas),
        elapsed_ms=_elapsed_ms,
    ).info(
        "[mcp-tool] registration COMPLETE agent={} servers={} succeeded={} failed={} "
        "total_tools={} elapsed_ms={}",
        agent_id, len(servers), succeeded_count, failed_count,
        len(all_tool_schemas), _elapsed_ms,
    )

    if all_tool_schemas:
        return ToolsSchema(standard_tools=all_tool_schemas)
    return None
