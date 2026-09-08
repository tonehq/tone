"""Fill empty profile variables from a connected CRM (MCP) at call start.

Two clearly separated parts (see the plan):
- **sync (DB)** — ``load_profile_crm_plan`` (in ``profile_context.py``) reads the
  per-agent config + the empty-and-mapped variables into a ``ProfileCrmPlan``.
  It runs in an executor alongside the profile-variable load, off the loop.
- **async (network)** — ``ProfileCrmEnrichmentService.enrich`` calls the CRM
  lookup tool via the ONE programmatic entry point
  (``McpServerService.call_tool``), parses the record, and maps each variable's
  ``crm_field`` dot-path onto ``{"profile.<key>": value}``.

Every failure degrades to ``{}`` (mirrors ``load_profile_context``): a slow or
broken CRM never fails the call — unfilled variables fall back to their inline
default (``{{key|default}}``) or render blank.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union
from uuid import UUID

from loguru import logger

from core.services.agents.crm_lookup_presets import get_crm_lookup_preset


@dataclass
class ProfileCrmPlan:
    """Resolved, per-call CRM enrichment plan (built by ``load_profile_crm_plan``)."""

    enabled: bool = False
    mcp_server_id: Optional[UUID] = None
    lookup_tool_name: Optional[str] = None
    phone_argument: Optional[str] = None
    # ``app_integrations.slug`` of the CRM (``hubspot``/``salesforce``/``zoho_crm``),
    # or None for a custom/other MCP → the generic single-phone-argument flow.
    crm_slug: Optional[str] = None
    # [(profile_key, crm_field), ...] — only EMPTY, mapped variables.
    fill_plan: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        if not (self.enabled and self.fill_plan and self.mcp_server_id):
            return False
        # A known CRM preset supplies both the tool and the phone shape, so
        # stored lookup_tool_name / phone_argument are not required for it. Any
        # other MCP keeps the original requirement (unchanged behavior).
        if get_crm_lookup_preset(self.crm_slug):
            return True
        return bool(self.lookup_tool_name and self.phone_argument)


class ProfileCrmEnrichmentService:
    """Async CRM lookup → ``{"profile.<key>": value}`` for empty mapped vars."""

    async def enrich(
        self,
        *,
        org_id: Optional[Union[str, UUID]],
        plan: ProfileCrmPlan,
        caller_phone: Optional[str],
    ) -> dict[str, str]:
        if not org_id or not plan.is_actionable or not (caller_phone or "").strip():
            return {}

        from core.database.session import get_db_context
        from core.services.mcp_server_service import McpServerService
        from core.services.agents.agent_profile_variable_service import PROFILE_PREFIX

        # A known CRM → its preset supplies the tool, the structured phone
        # request, and the response wrapper key. Otherwise the generic flow:
        # the stored tool + a plain {phone_argument: phone}.
        preset = get_crm_lookup_preset(plan.crm_slug)
        tool_name = plan.lookup_tool_name or (preset.default_tool_name if preset else None)
        arguments = (
            preset.build_arguments("phone", caller_phone)
            if preset
            else {plan.phone_argument: caller_phone}
        )
        record_prefix = preset.record_path if preset else ""

        try:
            with get_db_context() as db:
                record = await McpServerService(db, org_id=org_id).call_tool(
                    plan.mcp_server_id, tool_name, arguments
                )
        except Exception:  # noqa: BLE001 — enrichment must never break a call
            # phone is PII — never logged; the CRM record contents never logged.
            logger.exception(
                "[profile-crm] CRM lookup failed org={} tool={}", org_id, tool_name
            )
            return {}

        record = _first_record(record)
        if not isinstance(record, dict):
            return {}

        filled: dict[str, str] = {}
        for key, crm_field in plan.fill_plan:
            # For a preset CRM the record sits under a wrapper (results/records/
            # data), so crm_field is written relative to the record.
            path = f"{record_prefix}.{crm_field}" if record_prefix else crm_field
            value = _resolve_path(record, path)
            if value is not None:
                filled[f"{PROFILE_PREFIX}{key}"] = value
        return filled


def _first_record(record: Any) -> Any:
    """Some CRM tools return a list of matches — take the first (locked in
    grill-me). A dict is returned as-is; anything else is passed through."""
    if isinstance(record, list):
        return record[0] if record else None
    return record


# Sentinel distinguishing "path segment absent" from a legit ``None`` value.
_MISSING = object()


def _descend(data: Any, path: str) -> Any:
    """Walk a dot-path, taking the first element whenever a segment lands on a
    list. Returns the node at ``path``, or ``_MISSING`` if any segment is
    absent. Shared by ``extract_record`` and ``_resolve_path``."""
    cur: Any = data
    for seg in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict) or seg not in cur:
            return _MISSING
        cur = cur[seg]
    return cur


def extract_record(raw: Any, record_path: str) -> Optional[dict]:
    """Return the first matched record dict from a CRM tool response.

    Descends the preset's ``record_path`` wrapper (e.g. ``results``/``records``/
    ``data``) when present, taking the first element if it lands on a list.
    Returns ``None`` when there is no usable record. Shared by the mid-call
    ``find_customer`` tool (Layer 2)."""
    node = _descend(raw, record_path) if record_path else raw
    if node is _MISSING:
        return None
    node = _first_record(node)
    return node if isinstance(node, dict) else None


def _resolve_path(data: Any, path: str) -> Optional[str]:
    """Resolve a dot-path (e.g. ``properties.firstname``) to a scalar string.

    Walks nested dicts; when a segment lands on a list it takes the first
    element and continues. Returns ``None`` when the path is missing or lands on
    a non-scalar, so an unresolved mapping falls back to default/blank rather
    than injecting ``"{...}"`` into the prompt.
    """
    node = _descend(data, path)
    if node is _MISSING:
        return None
    node = _first_record(node)
    if node is None or isinstance(node, (dict, list)):
        return None
    return str(node)
