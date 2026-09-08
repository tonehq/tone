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


@dataclass
class ProfileCrmPlan:
    """Resolved, per-call CRM enrichment plan (built by ``load_profile_crm_plan``)."""

    enabled: bool = False
    mcp_server_id: Optional[UUID] = None
    lookup_tool_name: Optional[str] = None
    phone_argument: Optional[str] = None
    # [(profile_key, crm_field), ...] — only EMPTY, mapped variables.
    fill_plan: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return bool(
            self.enabled
            and self.fill_plan
            and self.mcp_server_id
            and self.lookup_tool_name
            and self.phone_argument
        )


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

        try:
            with get_db_context() as db:
                record = await McpServerService(db, org_id=org_id).call_tool(
                    plan.mcp_server_id,
                    plan.lookup_tool_name,
                    {plan.phone_argument: caller_phone},
                )
        except Exception:  # noqa: BLE001 — enrichment must never break a call
            # phone is PII — never logged; the CRM record contents never logged.
            logger.exception(
                "[profile-crm] CRM lookup failed org={} tool={}",
                org_id,
                plan.lookup_tool_name,
            )
            return {}

        record = _first_record(record)
        if not isinstance(record, dict):
            return {}

        filled: dict[str, str] = {}
        for key, crm_field in plan.fill_plan:
            value = _resolve_path(record, crm_field)
            if value is not None:
                filled[f"{PROFILE_PREFIX}{key}"] = value
        return filled


def _first_record(record: Any) -> Any:
    """Some CRM tools return a list of matches — take the first (locked in
    grill-me). A dict is returned as-is; anything else is passed through."""
    if isinstance(record, list):
        return record[0] if record else None
    return record


def _resolve_path(data: Any, path: str) -> Optional[str]:
    """Resolve a dot-path (e.g. ``properties.firstname``) to a scalar string.

    Walks nested dicts; when a segment lands on a list it takes the first
    element and continues. Returns ``None`` when the path is missing or lands on
    a non-scalar, so an unresolved mapping falls back to default/blank rather
    than injecting ``"{...}"`` into the prompt.
    """
    cur: Any = data
    for seg in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    if isinstance(cur, list):
        cur = cur[0] if cur else None
    if cur is None or isinstance(cur, (dict, list)):
        return None
    return str(cur)
