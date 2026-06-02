"""Custom tool service for voice agents — lets the LLM call customer-defined webhook tools and built-in tools during a call."""

import json
from typing import Any, Callable, List, Optional

import httpx
from fastapi import HTTPException
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from core.models.tool import Tool
from core.models.agent_tool import AgentTool
from core.utils.logging import truncate_for_log


def get_custom_tools_for_agent(agent_id: int) -> List[Tool]:
    """Fetch all active custom tools linked to an agent."""
    from core.database.session import get_db_context
    from core.services.tool_service import decrypt_auth_config

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

    # Decrypt auth_config for runtime use
    for tool in tools:
        tool.auth_config = decrypt_auth_config(tool.auth_config)

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


def create_custom_tool_handler(tool: Tool, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None):
    """Create a handler function for a custom tool that calls the customer's webhook."""

    async def handle_tool_call(params: FunctionCallParams) -> None:
        import time as _time

        arguments = params.arguments
        logger.info("Custom tool '{}' called with args: {}", tool.name, arguments)
        _t_start = _time.monotonic()
        tool_call_entry = {
            "tool": tool.name,
            "tool_type": tool.tool_type,
            "arguments": arguments,
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        try:
            # Build request headers
            headers = {"Content-Type": "application/json"}

            # Add auth headers based on auth_type
            auth_config = tool.auth_config or {}
            logger.info("Custom tool '{}' auth_type={}", tool.name, tool.auth_type)
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

        except Exception as e:
            logger.error("Custom tool '{}' failed: {}", tool.name, e)
            tool_call_entry["result"] = f"error: {str(e)}"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback(f"Error calling tool: {str(e)}")

    return handle_tool_call


def create_built_in_tool_handler(tool: Tool, caller_number: str, org_id=None, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None) -> Callable:
    """Create a handler for a built-in tool based on tool_type."""

    if tool.tool_type == "send_sms":
        return _create_send_sms_handler(tool, caller_number, tool_call_entries=tool_call_entries, current_turn=current_turn)
    elif tool.tool_type == "google_calendar":
        return _create_google_calendar_handler(tool, org_id=org_id, tool_call_entries=tool_call_entries, current_turn=current_turn)

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
        logger.info("Built-in tool 'send_sms' called. Sending SMS to {}", caller_number)
        _t_start = _time.monotonic()
        meta = tool.meta_data or {}
        recipient = meta.get("to_number") or caller_number
        tool_call_entry = {
            "tool": "send_sms",
            "tool_type": "send_sms",
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


def _create_google_calendar_handler(tool: Tool, org_id=None, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None) -> Callable:
    """Create a handler that creates/checks events via Google Calendar API."""

    async def handle_google_calendar(params: FunctionCallParams) -> None:
        import time as _time

        arguments = params.arguments
        action = arguments.get("action", "create_event")
        logger.info("Built-in tool 'google_calendar' called with action='{}', args={}", action, arguments)
        _t_start = _time.monotonic()
        tool_call_entry = {
            "tool": "google_calendar",
            "tool_type": "google_calendar",
            "arguments": {"action": action, **{k: v for k, v in arguments.items() if k != "action"}},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        meta = tool.meta_data or {}
        calendar_id = meta.get("calendar_id", "primary")
        timezone = meta.get("timezone", "UTC")
        # Use org_id from call context; fall back to meta_data for backward compatibility
        effective_org_id = org_id or meta.get("org_id")

        def _log_tool_call(result_str, duration_ms=None):
            tool_call_entry["result"] = result_str
            tool_call_entry["duration_ms"] = duration_ms or round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)

        if not effective_org_id:
            _log_tool_call("error: missing org_id")
            await params.result_callback("Error: Google Calendar tool is not configured. Missing org_id.")
            return

        # Get a valid access token (auto-refreshes if expired)
        try:
            from core.database.session import get_db_context
            from core.services.oauth_service import OAuthService

            if not tool.oauth_connection_id:
                logger.error("google_calendar: tool '{}' has no oauth_connection_id set", tool.name)
                _log_tool_call("error: no oauth_connection_id")
                await params.result_callback(
                    "Google Calendar tool is not linked to an OAuth connection. Please configure it in tool settings."
                )
                return

            with get_db_context() as db:
                svc = OAuthService(db, org_id=effective_org_id)
                connection = svc.get_connection(tool.oauth_connection_id)
                if not connection:
                    logger.error("google_calendar: OAuth connection {} not found for org {}", tool.oauth_connection_id, effective_org_id)
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
    ``duration_minutes``) or an **all-day event** when no time is given — so a date-only booking
    no longer fails. Google Calendar models all-day events with date-only ``start.date``/``end.date``
    where the end date is exclusive (i.e. the day after for a single-day event).
    """
    from datetime import datetime, timedelta

    title = arguments.get("title", "Appointment")
    date = arguments.get("date")  # e.g. "2026-05-10"
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
                end_obj = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                return "Error: invalid 'end_time'. Use HH:MM (24-hour)."
        if end_obj is None or end_obj <= start_obj:
            end_obj = start_obj + timedelta(minutes=duration_minutes)
        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_obj.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": timezone},
            "end": {"dateTime": end_obj.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": timezone},
        }
        when_str = f"on {date} at {start_time}"
    else:
        # No time supplied → all-day event (end date is exclusive, so use the next day).
        try:
            start_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return f"Error: invalid date '{date}'. Use YYYY-MM-DD."
        end_date = (start_date + timedelta(days=1)).strftime("%Y-%m-%d")
        event_body = {
            "summary": title,
            "description": description,
            "start": {"date": date},
            "end": {"date": end_date},
        }
        when_str = f"on {date} (all-day)"

    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    logger.info("google_calendar create_event request url={}/events body={}", base_url, event_body)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{base_url}/events", headers=headers, json=event_body)

    logger.info("google_calendar create_event response status={} body={}", response.status_code, response.text)
    if response.status_code in (200, 201):
        event = response.json()
        logger.info("google_calendar create_event SUCCESS: event_id={} status={} htmlLink={}", event.get("id"), event.get("status"), event.get("htmlLink"))
        return f"Event '{title}' created successfully {when_str}. Event link: {event.get('htmlLink', 'N/A')}"
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
