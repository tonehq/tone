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

        # A known CRM → its preset supplies the structured phone request and the
        # response wrapper key; the tool name is resolved against the server's
        # real tools (below). Otherwise the generic flow: the stored tool + a
        # plain {phone_argument: phone}.
        preset = get_crm_lookup_preset(plan.crm_slug)
        arguments = (
            preset.build_arguments("phone", caller_phone)
            if preset
            else {plan.phone_argument: caller_phone}
        )
        record_prefix = preset.record_path if preset else ""
        tool_name = plan.lookup_tool_name  # reassigned below once the DB is open

        try:
            with get_db_context() as db:
                # Preset CRM: resolve against the server's discovered tools —
                # the stored name is tried first but validated, so a stale saved
                # name can't bypass resolution. Generic MCP: use the stored tool
                # as-is (the user picked it from the real discovered list).
                if preset:
                    tool_name = resolve_preset_tool_name(
                        db, org_id, plan.mcp_server_id, preset, stored=plan.lookup_tool_name
                    )
                else:
                    tool_name = plan.lookup_tool_name
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


def resolve_preset_tool_name(db, org_id, mcp_server_id, preset, stored=None) -> str:
    """The tool name to call for a preset CRM — the server's ACTUAL tool name
    when a candidate matches its discovered tools, else the best-guess default.

    Resolving against the live tool list (instead of trusting a hardcoded name)
    is what makes the presets robust across CRM server variants — the same tool
    can be exposed as ``run_soql_query`` on one Salesforce server and ``query``
    on another. A ``stored`` name (the agent's saved config value) is tried
    FIRST but STILL validated against the discovered tools — so a stale/wrong
    saved name (e.g. an old preset default) can't bypass resolution. Never
    raises: on any error it falls back to the first candidate."""
    candidates = preset.candidates()
    # Stored value first (validated, not blindly trusted), then preset candidates.
    ordered = tuple(c for c in ((stored,) + tuple(candidates)) if c)
    try:
        from core.services.mcp_server_service import McpServerService

        actual = McpServerService(db, org_id=org_id).resolve_tool_name(
            mcp_server_id, ordered
        )
        if actual:
            return actual
    except Exception:  # noqa: BLE001 — resolution is best-effort
        logger.exception(
            "[profile-crm] tool-name resolution failed crm={} — using default",
            getattr(preset, "slug", None),
        )
    return candidates[0]


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
