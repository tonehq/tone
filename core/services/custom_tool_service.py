"""Custom tool service for voice agents — lets the LLM call customer-defined webhook tools and built-in tools during a call."""

import json
from typing import Any, Callable, List, Optional

import httpx
from fastapi import HTTPException
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


def create_built_in_tool_handler(tool: Tool, caller_number: str, org_id=None) -> Callable:
    """Create a handler for a built-in tool based on tool_type."""

    if tool.tool_type == "send_sms":
        return _create_send_sms_handler(tool, caller_number)
    elif tool.tool_type == "google_calendar":
        return _create_google_calendar_handler(tool, org_id=org_id)

    # Fallback: unknown built-in tool type
    async def noop_handler(params: FunctionCallParams) -> None:
        logger.warning("Unknown built-in tool type '{}' (name='{}')", tool.tool_type, tool.name)
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


def _create_google_calendar_handler(tool: Tool, org_id=None) -> Callable:
    """Create a handler that creates/checks events via Google Calendar API."""

    async def handle_google_calendar(params: FunctionCallParams) -> None:
        arguments = params.arguments
        action = arguments.get("action", "create_event")
        logger.info("Built-in tool 'google_calendar' called with action='{}', args={}", action, arguments)

        meta = tool.meta_data or {}
        calendar_id = meta.get("calendar_id", "primary")
        timezone = meta.get("timezone", "UTC")
        # Use org_id from call context; fall back to meta_data for backward compatibility
        effective_org_id = org_id or meta.get("org_id")

        if not effective_org_id:
            await params.result_callback("Error: Google Calendar tool is not configured. Missing org_id.")
            return

        # Get a valid access token (auto-refreshes if expired)
        try:
            from core.database.session import get_db_context
            from core.services.oauth_service import OAuthService

            with get_db_context() as db:
                svc = OAuthService(db, org_id=effective_org_id)
                connection = svc.get_connection_by_provider("google_calendar")
                if not connection:
                    logger.error("google_calendar: no OAuth connection found for org {}", effective_org_id)
                    await params.result_callback(
                        "Google Calendar is not connected. Please ask the admin to connect Google Calendar in the Integrations settings."
                    )
                    return
                access_token = svc.get_valid_access_token("google_calendar")
        except HTTPException as e:
            logger.error("google_calendar: OAuth error: {}", e.detail)
            if "reconnect" in str(e.detail).lower():
                await params.result_callback(
                    "Google Calendar connection has expired. Please ask the admin to reconnect Google Calendar in the Integrations settings."
                )
            else:
                await params.result_callback(f"Google Calendar is not available right now. Reason: {e.detail}")
            return
        except Exception as e:
            logger.error("google_calendar: unexpected error getting access token: {}", e)
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
            await params.result_callback(result)

        except httpx.TimeoutException:
            logger.error("google_calendar: Google API request timed out")
            await params.result_callback("Google Calendar is taking too long to respond. Please try again.")
        except Exception as e:
            logger.error("google_calendar tool failed: {}", e)
            await params.result_callback(f"Something went wrong with Google Calendar. Please try again later.")

    return handle_google_calendar


async def _calendar_create_event(base_url: str, headers: dict, arguments: dict, timezone: str) -> str:
    """Create a calendar event."""
    title = arguments.get("title", "Appointment")
    date = arguments.get("date")  # e.g. "2026-05-10"
    start_time = arguments.get("start_time")  # e.g. "14:00"
    duration_minutes = int(arguments.get("duration_minutes", 30))
    description = arguments.get("description", "")
    attendee_email = arguments.get("attendee_email")

    if not date or not start_time:
        return "Error: 'date' and 'start_time' are required to create an event."

    # Build start/end datetime strings
    start_dt = f"{date}T{start_time}:00"
    # Calculate end time
    start_hour, start_min = map(int, start_time.split(":"))
    total_minutes = start_hour * 60 + start_min + duration_minutes
    end_hour = total_minutes // 60
    end_min = total_minutes % 60
    end_dt = f"{date}T{end_hour:02d}:{end_min:02d}:00"

    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt, "timeZone": timezone},
        "end": {"dateTime": end_dt, "timeZone": timezone},
    }

    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{base_url}/events", headers=headers, json=event_body)

    if response.status_code in (200, 201):
        event = response.json()
        return f"Event '{title}' created successfully on {date} at {start_time} for {duration_minutes} minutes. Event link: {event.get('htmlLink', 'N/A')}"
    else:
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
