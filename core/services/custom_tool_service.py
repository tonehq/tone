"""Custom tool service for voice agents — lets the LLM call customer-defined webhook tools and built-in tools during a call."""

import json
import re
from types import SimpleNamespace
from typing import Any, Callable, List, Optional, Tuple

import httpx
from fastapi import HTTPException
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from core.config import settings
from core.models.tool import Tool
from core.models.agent_tool import AgentTool
from core.utils.logging import truncate_for_log
from core.utils.oauth_resolution import effective_of, stamp_effective

# Placeholder caller number used by test/preview calls; Twilio rejects it.
_PLACEHOLDER_CALLER_NUMBER = "+10000000000"


def _resolve_connection_header(tool: Tool) -> Optional[Tuple[str, str]]:
    """Return the ``(header_name, header_value)`` auth header for ``tool``'s
    linked connection, if any.

    The connection is the version-level override (``agent_tools.oauth_connection_id``)
    when the caller stamped it on the tool, otherwise the tool's own default.
    Works for every credential kind stored in ``oauth_connections``: 3-legged
    OAuth (refreshed transparently), static bearer credentials, and OAuth2
    client-credentials (minted on demand) resolve to ``Authorization: Bearer
    <token>``; API-key credentials resolve to their custom header (e.g.
    ``X-API-Key: <key>``) — all via ``OAuthService.resolve_connection_auth_header``.

    Opens a short-lived DB session because custom tool handlers run inside the
    voice pipeline (no request context). Any failure here is logged and
    swallowed so the call falls through (inline ``auth_config``, or no
    Authorization header) rather than crashing the agent's turn — the API call
    may still succeed for endpoints that don't require auth, and if it doesn't,
    the failure surfaces as a normal HTTP error the LLM can react to.
    """
    oauth_id = effective_of(tool)
    if not oauth_id:
        return None
    from core.database.session import get_db_context
    from core.services.oauth_service import OAuthService

    try:
        with get_db_context() as db:
            svc = OAuthService(db, org_id=tool.organization_id)
            connection = svc.get_connection(oauth_id)
            return svc.resolve_connection_auth_header(connection)
    except Exception as exc:
        logger.warning(
            "Custom tool '{}' connection credential resolution failed ({}); falling back to "
            "inline credentials so the request still goes out",
            tool.name,
            exc,
        )
        return None


def get_custom_tools_for_agent(agent_id: int) -> List[Tool]:
    """Fetch all active custom tools linked to an agent's published version.

    The link table's ``oauth_connection_id`` (per-version override) is selected
    in the same query and stamped onto each Tool as ``effective_oauth_connection_id``
    — see ``core.utils.oauth_resolution``. Handlers read that attribute instead
    of ``tool.oauth_connection_id`` so the override rule stays in one place and
    the fetch stays a single round-trip.
    """
    from core.database.session import get_db_context
    from core.services.tool_service import decrypt_auth_config
    from core.utils.agent_scope import published_config_subquery

    # Attachments are per-version: filter to the agent's published config so
    # the runtime never picks up draft-version tools.
    published_config_sq = published_config_subquery(agent_id)

    with get_db_context() as db:
        rows = (
            db.query(Tool, AgentTool.oauth_connection_id)
            .join(AgentTool, AgentTool.tool_id == Tool.id)
            .filter(
                AgentTool.agent_id == agent_id,
                AgentTool.agent_config_id == published_config_sq,
                Tool.is_active == True,
            )
            .all()
        )
        tools: List[Tool] = []
        for tool, link_oauth in rows:
            stamp_effective(tool, link_oauth)
            db.expunge(tool)
            tools.append(tool)

    # Decrypt auth_config for runtime use
    for tool in tools:
        tool.auth_config = decrypt_auth_config(tool.auth_config)

    logger.info("Found {} custom tools for agent {}", len(tools), agent_id)
    return tools


# Tool fields the schema builder + handlers read. Serialized into the agent pipeline
# cache so the builder can rebuild tools/handlers without a DB query. `id` and
# `mcp_server_id` are also cached so the call-log snapshot can list/filter tools
# without re-querying the DB at call-insert time.
_CACHED_TOOL_FIELDS = (
    "id", "name", "description", "tool_type", "parameters",
    "url", "method", "auth_type", "auth_config", "meta_data",
    "oauth_connection_id", "effective_oauth_connection_id", "mcp_server_id",
)


def serialize_agent_tools(agent_id: int) -> List[dict]:
    """Fetch the agent's active tools and return JSON-serializable dicts (auth_config
    decrypted) for the pipeline cache. The builder rebuilds handlers from these via
    `tool_from_cache` — no per-call DB query for tools."""
    tools = get_custom_tools_for_agent(agent_id)
    out: List[dict] = []
    for t in tools:
        d = {f: getattr(t, f, None) for f in _CACHED_TOOL_FIELDS}
        # UUID columns must be stringified to survive a JSON round-trip through Redis.
        for k in ("id", "oauth_connection_id", "effective_oauth_connection_id", "mcp_server_id"):
            if d.get(k) is not None:
                d[k] = str(d[k])
        out.append(d)
    return out


def tool_from_cache(d: dict) -> SimpleNamespace:
    """Reconstruct a lightweight tool object from a cached dict. Exposes the same
    attributes (`.name`, `.tool_type`, `.auth_config`, …) the handlers/schema builder
    read, so they work unchanged whether given an ORM Tool or this."""
    return SimpleNamespace(**d)


def sanitize_tool_name(name: str) -> str:
    """Make a tool name safe for LLM function-calling APIs.

    OpenAI/Anthropic require function names to match ^[a-zA-Z0-9_-]+$ (no spaces,
    max 64 chars). User-named tools like "calender tool" otherwise trigger a 400
    ("string does not match pattern"). The schema name and the registered handler
    name MUST be sanitized identically so the model's tool call still maps back to
    its handler.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", (name or "").strip())
    return (cleaned or "tool")[:64]


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
            name=sanitize_tool_name(tool.name),
            description=tool.description,
            properties=properties,
            required=required,
        )
        function_schemas.append(schema)
        logger.info("Built schema for custom tool: {} (fn name: {})", tool.name, schema.name)

    return ToolsSchema(standard_tools=function_schemas)


_MAX_RESPONSE_CHARS = 8000
_BLOCKED_HOST_SUFFIXES = (".internal", ".local")
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}


def _assert_safe_url(url: str) -> None:
    """SSRF guard: require https:// and reject loopback/private/link-local/metadata hosts.
    Hostnames are not DNS-resolved here (DNS-rebinding SSRF is out of scope for v1)."""
    import ipaddress
    import socket
    import urllib.parse

    parsed = urllib.parse.urlparse(url or "")
    if parsed.scheme != "https":
        raise ValueError("Only https:// URLs are allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL has no host")
    if host in _BLOCKED_HOSTS or any(host.endswith(s) for s in _BLOCKED_HOST_SUFFIXES):
        raise ValueError("Blocked host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
        try:
            ip = ipaddress.ip_address(socket.inet_aton(host))
        except (OSError, ValueError):
            ip = None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    ):
        raise ValueError("Blocked private/loopback/link-local IP")


def _interp(text, ctx: dict):
    """Interpolate {{var}} in a string from ctx (LLM args). Non-strings pass through.
    Header values get CR/LF stripped to prevent header injection."""
    if not isinstance(text, str):
        return text
    from core.services.pipeline.prompt_variables import substitute_variables

    return substitute_variables(text, ctx) or ""


def create_custom_tool_handler(tool: Tool, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None):
    """Create a handler function for a custom tool that calls the customer's webhook.

    Also powers workflow **API Request** nodes: if the tool object carries ``headers``
    (dict) and/or ``static_body`` (dict), those are merged in and ``{{var}}``-interpolated
    from the LLM-provided args, with an SSRF/HTTPS guard and a response-size cap."""

    async def handle_tool_call(params: FunctionCallParams) -> None:
        import time as _time

        arguments = params.arguments
        logger.info("Custom tool '{}' called with args: {}", tool.name, arguments)
        _t_start = _time.monotonic()
        tool_call_entry = {
            "tool": tool.name,
            "tool_type": tool.tool_type,
            "tool_id": str(tool.id) if tool.id else None,
            "arguments": arguments,
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        try:
            # Build request headers
            headers = {"Content-Type": "application/json"}

            # Add auth headers. A linked connection (per-assignment override →
            # tool default, see core/utils/oauth_resolution.py) wins over inline
            # ``auth_config`` regardless of auth_type. OAuth / bearer /
            # client-credentials connections resolve to a bearer token, minted
            # fresh on every call so an in-flight refresh mid-conversation never
            # leaves a stale token; API-key connections resolve to their custom
            # header (e.g. ``X-API-Key``). Inline credentials are the fallback
            # when no connection is linked (or its resolution failed — fail-open,
            # logged in the resolver).
            auth_config = tool.auth_config or {}
            connection_id = effective_of(tool)
            logger.info("Custom tool '{}' auth_type={}", tool.name, tool.auth_type)
            conn_header = _resolve_connection_header(tool) if connection_id else None
            if conn_header:
                headers[conn_header[0]] = conn_header[1]
            elif tool.auth_type == "api_key":
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
            elif tool.auth_type == "oauth" and not connection_id:
                logger.warning(
                    "Custom tool '{}' has auth_type='oauth' but no linked connection; "
                    "calling without an Authorization header",
                    tool.name,
                )

            extra_headers = getattr(tool, "headers", None)
            if isinstance(extra_headers, dict):
                for hk, hv in extra_headers.items():
                    if not hk:
                        continue
                    val = _interp(hv, arguments)
                    headers[str(hk)] = str(val).replace("\r", "").replace("\n", "")

            url = _interp(tool.url, arguments)
            remaining_args = dict(arguments)
            for key, value in arguments.items():
                placeholder = "{" + key + "}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
                    remaining_args.pop(key)

            if getattr(tool, "is_workflow_api_request", False):
                _assert_safe_url(url)

            static_body = getattr(tool, "static_body", None)
            if isinstance(static_body, dict) and static_body:
                body = {k: _interp(v, arguments) for k, v in static_body.items()}
                body.update(remaining_args)
            else:
                body = remaining_args

            async with httpx.AsyncClient(timeout=30.0) as client:
                if tool.method.upper() == "GET":
                    response = await client.get(url, params=body, headers=headers)
                else:
                    response = await client.request(
                        method=tool.method.upper(),
                        url=url,
                        json=body,
                        headers=headers,
                    )

            try:
                result = response.json()
                result_text = json.dumps(result)
            except Exception:
                result_text = response.text
            if isinstance(result_text, str) and len(result_text) > _MAX_RESPONSE_CHARS:
                result_text = result_text[:_MAX_RESPONSE_CHARS] + "…(truncated)"
            if response.status_code >= 400:
                result_text = f"(HTTP {response.status_code}) {result_text}"

            logger.info(
                "🔧 Custom tool result ← tool='{}' status={} args={} output={}",
                tool.name,
                response.status_code,
                truncate_for_log(arguments),
                truncate_for_log(result_text),
            )

            tool_call_entry["result"] = "success"
            tool_call_entry["status_code"] = response.status_code
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)

            await params.result_callback(result_text)

        except httpx.TimeoutException:
            logger.warning("Custom tool '{}' timed out", tool.name)
            tool_call_entry["result"] = "error: timeout"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback("The request timed out. Please tell the caller and continue.")
        except Exception as e:
            logger.error("Custom tool '{}' failed: {}", tool.name, e)
            tool_call_entry["result"] = f"error: {str(e)}"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback(f"The request could not be completed: {str(e)}")

    return handle_tool_call


def create_built_in_tool_handler(tool: Tool, caller_number: str, org_id=None, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None, tool_dedup: Optional[dict] = None) -> Callable:
    """Create a handler for a built-in tool based on tool_type."""

    if tool.tool_type == "send_sms":
        return _create_send_sms_handler(tool, caller_number, tool_call_entries=tool_call_entries, current_turn=current_turn)
    elif tool.tool_type == "google_calendar":
        return _create_google_calendar_handler(tool, org_id=org_id, tool_call_entries=tool_call_entries, current_turn=current_turn, tool_dedup=tool_dedup)

    # Fallback: unknown built-in tool type
    async def noop_handler(params: FunctionCallParams) -> None:
        logger.warning("Unknown built-in tool type '{}' (name='{}')", tool.tool_type, tool.name)
        await params.result_callback(f"Unknown built-in tool: {tool.name}")

    return noop_handler


def _create_send_sms_handler(tool: Tool, caller_number: str, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None) -> Callable:
    """Create a handler that sends an SMS via Twilio."""

    async def handle_send_sms(params: FunctionCallParams) -> None:
        import time as _time

        arguments = params.arguments
        message = arguments.get("message", "")
        logger.info("Built-in tool 'send_sms' called (caller_number={})", caller_number)
        _t_start = _time.monotonic()
        meta = tool.meta_data or {}
        recipient = (meta.get("to_number") or caller_number or "").strip()
        if recipient in ("", _PLACEHOLDER_CALLER_NUMBER):
            default_to = (settings.SEND_SMS_DEFAULT_TO_NUMBER or "").strip()
            if default_to:
                logger.info(
                    "send_sms: recipient '{}' is empty/placeholder — using SEND_SMS_DEFAULT_TO_NUMBER '{}'",
                    recipient or "(empty)", default_to,
                )
                recipient = default_to
        tool_call_entry = {
            "tool": "send_sms",
            "tool_type": "send_sms",
            "tool_id": str(tool.id) if tool.id else None,
            "arguments": {"message": message, "to": recipient},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        auth = tool.auth_config or {}
        account_sid = auth.get("account_sid")
        auth_token = auth.get("auth_token")
        from_number = meta.get("from_number")

        if not all([account_sid, auth_token, from_number]):
            logger.error("send_sms tool missing Twilio credentials in auth_config or from_number in meta_data")
            tool_call_entry["result"] = "error: missing Twilio credentials"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback("Error: SMS tool is not configured. Missing Twilio credentials.")
            return

        if not recipient:
            logger.error("send_sms tool: no recipient phone number available")
            tool_call_entry["result"] = "error: no recipient number"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback("Error: No recipient phone number is available for this call.")
            return

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    auth=(account_sid, auth_token),
                    data={
                        "From": from_number,
                        "To": recipient,
                        "Body": message,
                    },
                )

            if response.status_code == 201:
                logger.info("SMS sent successfully to {}", recipient)
                tool_call_entry["result"] = "success"
                tool_call_entry["status_code"] = response.status_code
                tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
                if tool_call_entries is not None:
                    tool_call_entries.append(tool_call_entry)
                await params.result_callback("SMS sent successfully.")
            else:
                error_detail = response.text
                logger.error("SMS sending failed: status={} body={}", response.status_code, error_detail)
                tool_call_entry["result"] = f"error: status {response.status_code}"
                tool_call_entry["status_code"] = response.status_code
                tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
                if tool_call_entries is not None:
                    tool_call_entries.append(tool_call_entry)
                await params.result_callback(f"Failed to send SMS: {error_detail}")

        except Exception as e:
            logger.error("send_sms tool failed: {}", e)
            tool_call_entry["result"] = f"error: {str(e)}"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback(f"Error sending SMS: {str(e)}")

    return handle_send_sms


def _create_google_calendar_handler(tool: Tool, org_id=None, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None, tool_dedup: Optional[dict] = None) -> Callable:
    """Create a handler that creates/checks events via Google Calendar API."""

    async def handle_google_calendar(params: FunctionCallParams) -> None:
        import time as _time
        from core.utils.tool_idempotency import booking_signature, is_cacheable_result

        arguments = params.arguments
        action = arguments.get("action", "create_event")
        logger.info("Built-in tool 'google_calendar' called with action='{}', args={}", action, arguments)
        _t_start = _time.monotonic()
        tool_call_entry = {
            "tool": "google_calendar",
            "tool_type": "google_calendar",
            "tool_id": str(tool.id) if tool.id else None,
            "arguments": {"action": action, **{k: v for k, v in arguments.items() if k != "action"}},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        def _log_tool_call(result_str, duration_ms=None):
            tool_call_entry["result"] = result_str
            tool_call_entry["duration_ms"] = duration_ms or round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)

        # In-call idempotency: suppress a duplicate create_event (e.g. a barge-in
        # discarded the first result and the LLM re-issued the booking) so we don't
        # create a second calendar event for the same booking.
        sig = booking_signature("google_calendar", arguments, is_create=(action == "create_event")) if tool_dedup is not None else None
        if sig is not None and sig in tool_dedup:
            cached = tool_dedup[sig]
            logger.warning(
                "⏭️ Duplicate google_calendar create_event suppressed (already created this call); returning cached result"
            )
            tool_call_entry["status"] = "duplicate_suppressed"
            _log_tool_call(cached)
            await params.result_callback(cached)
            return

        meta = tool.meta_data or {}
        calendar_id = meta.get("calendar_id", "primary")
        timezone = meta.get("timezone", "UTC")
        # Use org_id from call context; fall back to meta_data for backward compatibility
        effective_org_id = org_id or meta.get("org_id")

        if not effective_org_id:
            _log_tool_call("error: missing org_id")
            await params.result_callback("Error: Google Calendar tool is not configured. Missing org_id.")
            return

        # Get a valid access token (auto-refreshes if expired)
        try:
            from core.database.session import get_db_context
            from core.services.oauth_service import OAuthService

            resolved_oauth_id = effective_of(tool)
            if not resolved_oauth_id:
                logger.error("google_calendar: tool '{}' has no oauth_connection_id set", tool.name)
                _log_tool_call("error: no oauth_connection_id")
                await params.result_callback(
                    "Google Calendar tool is not linked to an OAuth connection. Please configure it in tool settings."
                )
                return

            with get_db_context() as db:
                svc = OAuthService(db, org_id=effective_org_id)
                connection = svc.get_connection(resolved_oauth_id)
                if not connection:
                    logger.error("google_calendar: OAuth connection {} not found for org {}", resolved_oauth_id, effective_org_id)
                    _log_tool_call("error: OAuth connection not found")
                    await params.result_callback(
                        "Google Calendar connection not found. Please reconnect Google Calendar in the Integrations settings."
                    )
                    return
                access_token = svc.get_valid_access_token_for_connection(connection)
        except HTTPException as e:
            logger.error("google_calendar: OAuth error: {}", e.detail)
            _log_tool_call(f"error: OAuth - {e.detail}")
            if "reconnect" in str(e.detail).lower():
                await params.result_callback(
                    "Google Calendar connection has expired. Please ask the admin to reconnect Google Calendar in the Integrations settings."
                )
            else:
                await params.result_callback(f"Google Calendar is not available right now. Reason: {e.detail}")
            return
        except Exception as e:
            logger.error("google_calendar: unexpected error getting access token: {}", e)
            _log_tool_call(f"error: {str(e)}")
            await params.result_callback("Google Calendar is temporarily unavailable. Please try again later.")
            return

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        base_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}"

        try:
            if action == "check_availability":
                result = await _calendar_check_availability(base_url, headers, arguments, timezone)
            elif action == "create_event":
                result = await _calendar_create_event(base_url, headers, arguments, timezone)
            elif action == "list_events":
                result = await _calendar_list_events(base_url, headers, arguments, timezone)
            else:
                result = f"Unknown action: {action}. Supported actions: create_event, check_availability, list_events"

            logger.info("google_calendar action='{}' result: {}", action, result)
            _log_tool_call("success")
            # Cache the successful create_event so an interruption-driven retry
            # within this call returns this result instead of creating a duplicate.
            # Skip caching failures so a retry can still complete the booking.
            if sig is not None and tool_dedup is not None and is_cacheable_result(result):
                tool_dedup[sig] = result
            await params.result_callback(result)

        except httpx.TimeoutException:
            logger.error("google_calendar: Google API request timed out")
            _log_tool_call("error: timeout")
            await params.result_callback("Google Calendar is taking too long to respond. Please try again.")
        except Exception as e:
            logger.error("google_calendar tool failed: {}", e)
            _log_tool_call(f"error: {str(e)}")
            await params.result_callback(f"Something went wrong with Google Calendar. Please try again later.")

    return handle_google_calendar


async def _calendar_create_event(base_url: str, headers: dict, arguments: dict, timezone: str) -> str:
    """Create a calendar event.

    Accepts either a timed event (``start_time`` provided, with optional ``end_time`` or
    ``duration_minutes``; an optional ``end_date`` lets a timed slot run overnight) or an
    **all-day event** when no time is given — so a date-only booking no longer fails. Google
    Calendar models all-day events with date-only ``start.date``/``end.date`` where the end date is
    exclusive: a single-day event ends the next day, and a multi-day stay (``end_date`` given, e.g.
    a hotel check-out) ends on that date.
    """
    from datetime import datetime, timedelta

    title = arguments.get("title", "Appointment")
    date = arguments.get("date")  # check-in / event date, e.g. "2026-11-01"
    end_date = arguments.get("end_date")  # check-out date for multi-day stays
    start_time = arguments.get("start_time")  # e.g. "14:00"
    end_time = arguments.get("end_time")  # e.g. "16:00" (optional)
    duration_minutes = int(arguments.get("duration_minutes", 30) or 30)
    description = arguments.get("description", "")
    attendee_email = arguments.get("attendee_email")

    if not date:
        return "Error: 'date' is required to create an event."

    if start_time:
        # Timed event — compute end via end_time when given, else duration. datetime math keeps
        # this correct across midnight and rejects malformed input instead of producing bad strings.
        # An explicit end_date lets a timed slot run to the next day (overnight bookings).
        try:
            start_obj = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return (
                f"Error: invalid date/time ('{date}' '{start_time}'). "
                "Use date as YYYY-MM-DD and time as HH:MM (24-hour)."
            )
        end_obj = None
        if end_time:
            try:
                end_obj = datetime.strptime(f"{end_date or date} {end_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                return (
                    "Error: invalid 'end_time'/'end_date'. "
                    "Use date as YYYY-MM-DD and time as HH:MM (24-hour)."
                )
        if end_obj is None or end_obj <= start_obj:
            end_obj = start_obj + timedelta(minutes=duration_minutes)
        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_obj.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": timezone},
            "end": {"dateTime": end_obj.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": timezone},
        }
        when_desc = f"{date} at {start_time}"
    else:
        # No time supplied → all-day event. A provided end_date spans a multi-day stay (e.g. a
        # hotel booking); Google all-day events use date-only start/end where end.date is EXCLUSIVE,
        # so a single-day event ends on the next day and a stay ends on the check-out date.
        try:
            start_date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return f"Error: invalid date '{date}'. Use YYYY-MM-DD."
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return f"Error: invalid 'end_date' '{end_date}'. Use YYYY-MM-DD."
            all_day_end = end_date
            when_desc = f"{date} to {end_date} (all-day)"
        else:
            all_day_end = (start_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
            when_desc = f"{date} (all-day)"
        event_body = {
            "summary": title,
            "description": description,
            "start": {"date": date},
            "end": {"date": all_day_end},
        }

    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    logger.info("google_calendar create_event request url={}/events body={}", base_url, event_body)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{base_url}/events", headers=headers, json=event_body)

    logger.info("google_calendar create_event response status={} body={}", response.status_code, response.text)
    if response.status_code in (200, 201):
        event = response.json()
        logger.info("google_calendar create_event SUCCESS: event_id={} status={} htmlLink={}", event.get("id"), event.get("status"), event.get("htmlLink"))
        return f"Event '{title}' created successfully ({when_desc}). Event link: {event.get('htmlLink', 'N/A')}"
    else:
        logger.error("google_calendar create_event FAILED: status={} body={}", response.status_code, response.text)
        return f"Failed to create event: {response.text}"


async def _calendar_check_availability(base_url: str, headers: dict, arguments: dict, timezone: str) -> str:
    """Check availability for a given date/time."""
    date = arguments.get("date")  # e.g. "2026-05-10"
    start_time = arguments.get("start_time", "09:00")
    end_time = arguments.get("end_time", "17:00")

    if not date:
        return "Error: 'date' is required to check availability."

    time_min = f"{date}T{start_time}:00"
    time_max = f"{date}T{end_time}:00"

    params = {
        "timeMin": f"{time_min}+00:00" if "+" not in time_min else time_min,
        "timeMax": f"{time_max}+00:00" if "+" not in time_max else time_max,
        "timeZone": timezone,
        "singleEvents": "true",
        "orderBy": "startTime",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/events", headers=headers, params=params)

    if response.status_code != 200:
        return f"Failed to check availability: {response.text}"

    events = response.json().get("items", [])
    if not events:
        return f"No events found on {date} between {start_time} and {end_time}. The calendar is free."

    busy_slots = []
    for event in events:
        start = event.get("start", {}).get("dateTime", "unknown")
        end = event.get("end", {}).get("dateTime", "unknown")
        summary = event.get("summary", "Busy")
        busy_slots.append(f"- {summary}: {start} to {end}")

    return f"Found {len(events)} event(s) on {date}:\n" + "\n".join(busy_slots)


async def _calendar_list_events(base_url: str, headers: dict, arguments: dict, timezone: str) -> str:
    """List upcoming events."""
    import time as time_module

    max_results = int(arguments.get("max_results", 5))
    date = arguments.get("date")

    if date:
        time_min = f"{date}T00:00:00+00:00"
        time_max = f"{date}T23:59:59+00:00"
    else:
        from datetime import datetime, timezone as tz
        now = datetime.now(tz.utc).isoformat()
        time_min = now
        time_max = None

    params = {
        "timeMin": time_min,
        "maxResults": str(max_results),
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeZone": timezone,
    }
    if time_max:
        params["timeMax"] = time_max

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/events", headers=headers, params=params)

    if response.status_code != 200:
        return f"Failed to list events: {response.text}"

    events = response.json().get("items", [])
    if not events:
        return "No upcoming events found."

    event_list = []
    for event in events:
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "unknown"))
        summary = event.get("summary", "No title")
        event_list.append(f"- {summary}: {start}")

    return f"Found {len(events)} event(s):\n" + "\n".join(event_list)
