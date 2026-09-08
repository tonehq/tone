"""find_customer: LLM-driven mid-call CRM lookup tool (Layer 2).

Registered only when the agent has CRM enrichment enabled for a preset CRM
(HubSpot / Salesforce / Zoho). It lets the agent look the caller up in that CRM
mid-conversation by phone / email / name — the fallback when the call-start
phone match (Layer 1) misses (different number) or the business wants to search
by email/name. Reuses the SAME per-CRM presets as Layer 1.

The value the caller provides is a lookup key, NOT proof of identity — sensitive
actions should still be verified separately (future Layer 3).
"""

import json
import time as _time
from typing import Callable, List, Optional

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from core.services.agents.crm_lookup_presets import get_crm_lookup_preset
from core.services.agents.crm_lookup_presets.base import LOOKUP_FIELDS
from core.services.agents.profile_crm_enrichment_service import extract_record
from core.services.pipeline.tool_call_timing import ToolCallTimer, finalize_and_record

FIND_CUSTOMER_TOOL_NAME = "find_customer"

FIND_CUSTOMER_TOOL_SCHEMA = FunctionSchema(
    name=FIND_CUSTOMER_TOOL_NAME,
    description=(
        "Look the current caller up in the connected CRM to fetch their "
        "details (name, email, past records, etc.). Use this when you don't "
        "already know who the caller is — for example the call-start lookup "
        "found nothing, or the caller is on a different number. Ask the caller "
        "for their email or full name first, then call this tool. Returns the "
        "matched customer record as JSON, or a not-found message."
    ),
    properties={
        "field": {
            "type": "string",
            "enum": list(LOOKUP_FIELDS),
            "description": "Which identifier you are searching by.",
        },
        "value": {
            "type": "string",
            "description": "The caller's phone number, email, or full name.",
        },
    },
    required=["field", "value"],
)

FIND_CUSTOMER_SYSTEM_PROMPT = (
    "## Looking up the caller\n"
    "You have a tool called `find_customer` that looks the caller up in the "
    "connected CRM. If you do not already know who the caller is (their details "
    "were not provided at the start of the call), ask them politely for the "
    "email address or full name on their account, then call `find_customer` "
    "with the value they give. Use the returned record to personalize the "
    "conversation. If no match is found, continue helping them as a new caller. "
    "Treat what the caller tells you as a lookup key only — for any sensitive "
    "or account-changing action, verify their identity separately.\n\n"
)


def prepend_find_customer_instructions(messages: List[dict]) -> List[dict]:
    """Prepend the find_customer guidance to the first system message.

    Prepended (not appended) so the agent author's own prompt comes after and
    can override it — mirrors ``messages_with_date_anchor``. Returns a new list;
    never mutates. No-op if there is no system message.
    """
    out: List[dict] = []
    injected = False
    for m in messages:
        if not injected and m.get("role") == "system":
            out.append({**m, "content": FIND_CUSTOMER_SYSTEM_PROMPT + (m.get("content") or "")})
            injected = True
        else:
            out.append(m)
    return out


def create_find_customer_handler(
    *,
    org_id,
    mcp_server_id,
    crm_slug: str,
    tool_call_entries: Optional[list] = None,
    tool_request_ts: Optional[dict] = None,
    current_turn: Optional[dict] = None,
) -> Callable:
    """Factory: an async handler that runs a CRM lookup via the CRM's preset.

    Bound at build time to the agent's CRM (``mcp_server_id`` + ``crm_slug``).
    Builds the per-CRM request with the preset, calls the tool via the single
    programmatic entry point (``McpServerService.call_tool``), and returns the
    matched record as compact JSON. Any failure returns a safe message — a CRM
    lookup must never crash the call. No phone/email/name value or record
    contents are ever logged.
    """

    async def handle_find_customer(params: FunctionCallParams) -> None:
        args = params.arguments or {}
        field = (args.get("field") or "").strip().lower()
        value = (args.get("value") or "").strip()
        _t_start = _time.monotonic()
        timer = ToolCallTimer.start(params, tool_request_ts)
        entry = {
            "tool": FIND_CUSTOMER_TOOL_NAME,
            "tool_type": "built_in",
            "arguments": {"field": field},  # value is PII — not logged
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
            **timer.initial_fields(),
        }

        result_text = "No matching customer found."
        try:
            preset = get_crm_lookup_preset(crm_slug)
            if preset is None or field not in LOOKUP_FIELDS or not value:
                result_text = "Could not run the lookup — need a phone, email, or name."
            else:
                from core.database.session import get_db_context
                from core.services.mcp_server_service import McpServerService

                lookup_args = preset.build_arguments(field, value)
                with get_db_context() as db:
                    raw = await McpServerService(db, org_id=org_id).call_tool(
                        mcp_server_id, preset.default_tool_name, lookup_args
                    )
                record = extract_record(raw, preset.record_path)
                if record:
                    result_text = json.dumps(record)
            entry["result"] = "ok"
        except Exception as e:  # noqa: BLE001 — a lookup must never break the call
            logger.exception(
                "[find-customer-tool] lookup failed crm={} field={}", crm_slug, field
            )
            entry["result"] = f"error: {e}"
            result_text = "The customer lookup could not be completed right now."

        entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
        finalize_and_record(entry, timer, tool_call_entries)
        await params.result_callback(result_text)

    return handle_find_customer
