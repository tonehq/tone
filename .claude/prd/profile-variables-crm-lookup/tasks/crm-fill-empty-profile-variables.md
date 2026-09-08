# crm-fill-empty-profile-variables

> feature: profile-variables-crm-lookup · task: crm-fill-empty-profile-variables

## Requirements

Fill empty profile variables from a connected CRM MCP at call start, on the **prompt path only**.

- Match the caller in the CRM by **phone number** (`call_data["from"]`).
- Fill **only** profile variables whose stored value is empty; never overwrite a user-set value.
- Field mapping is **configured by the agent builder** in the Profile Variables screen, **auto-suggested**
  by name and editable; saved per agent.
- The CRM **lookup tool is auto-detected** from the attached CRM MCP's tools and **confirmed by the user**.
- On **no match / error / timeout**, fall back to the variable's inline default (`{{k|default}}`) or blank;
  **never fail the call**.
- Non-goals: workflow-engine path, per-caller CRM tokens, email match, CRM write-back, cross-call caching.

## Implementation Details

- **Runtime hook:** in `core/services/pipeline/runner/pipecat.py` (~lines 284–300), after `profile_vars`
  are loaded and before `build_call_context`, run a guarded, timed-out enrichment step for empty keys.
  Prefer routing it through/next to `load_profile_context` (`core/services/agents/profile_context.py`) so a
  future workflow path reuses the same seam.
- **Enrichment service (new, `BaseService`):** input = caller phone + attached CRM + mapping + empty keys;
  output = `{profile.<key>: value}` for keys it could fill. Calls the CRM **directly** (not via the LLM)
  using existing `mcp_tool_service` helpers: `get_mcp_servers_for_agent`, `build_mcp_request_headers`,
  `resolve_server_url`, Pipecat `MCPClient.start()` + session `list_tools()`/tool call. Degrade to `{}` on
  any failure (mirror `load_profile_context`).
- **Mapping storage + migration:** persist per-agent mapping (variable → CRM field) and the chosen lookup
  tool. Decide: JSON column / new columns on `agent_profile_variables`, or a small mapping model. Ship a
  safe Alembic migration.
- **API:** org-scoped endpoints to (a) list the CRM's lookup-tool candidates + fields for auto-suggest,
  (b) GET/PUT the per-agent mapping + chosen tool. Reuse `AgentProfileVariableService` where possible.
- **Frontend:** extend the Profile Variables screen (`frontend/src/components/agents/profile-variables/*`)
  with a per-variable CRM-field dropdown (auto-suggested) and a lookup-tool confirm; wire via existing
  `agentProfileVariables` hooks/service/types. Use shared components (`CustomButton`, `SelectInput`, …).

## Acceptance Criteria

- [ ] Caller in CRM + mapping set → empty vars filled and substituted in the prompt.
- [ ] User-set variable values are never overwritten.
- [ ] No match / error / timeout → default or blank, call still connects and runs.
- [ ] Mapping + confirmed lookup tool persist per agent and drive enrichment.
- [ ] Enrichment errors logged with traceback; CRM token never logged.
- [ ] Logic in a service, reuses MCP/profile helpers; safe migration; tests added; lint + typecheck pass.

---

## Addendum — Per-CRM lookup presets (HubSpot / Salesforce / Zoho)

**Added 2026-09-08.** Extends this task: the three app-integrated CRMs each expose a differently-shaped
lookup, so auto-suggesting a single `phone_argument` is not enough for two of them. When the user selects
one of these three CRM servers, the correct tool **and** the correctly-structured phone request must
auto-fill; any other/custom MCP keeps the existing generic pick-tool + phone-argument flow.

### Requirements (addendum)
- Detect which of the three CRMs a selected MCP server is, via its `app_integration.slug`
  (`hubspot` / `salesforce` / `zoho_crm`).
- Per-CRM preset = the lookup tool + how the caller phone is placed into the request:
  - **zoho_crm** → tool `Search Records`, plain arg `phone` (module `Contacts`).
  - **hubspot** → tool `hubspot-search-objects`, filter object
    `{object_type:"contacts", filters:[{propertyName:"phone", operator:"EQ", value:<phone>}]}`.
  - **salesforce** → tool `Query`, SOQL string `SELECT ... FROM Contact WHERE Phone = '<phone>'`.
- The three tool names/shapes are the current official values; the actual tool list is still discovered
  live, so a preset only PRE-FILLS (the user can still change it).
- Any non-preset CRM → unchanged generic flow (pick tool from discovered list + choose phone argument).
- Must not affect existing functionality: the generic path, the single-phone-argument model, and every
  already-working (non-preset) MCP stay exactly as they are.

### Acceptance Criteria (addendum)
- [ ] Selecting a HubSpot / Salesforce / Zoho CRM server auto-fills the correct tool + request shape.
- [ ] At call time the caller phone is placed into the correct shape per CRM (plain / filter / SOQL) and
      the record is fetched + mapped to variables.
- [ ] A custom/other MCP behaves exactly as before (generic flow untouched).
- [ ] No regression to the existing crm_field / config / enrichment behavior; tests added for each preset
      builder.

---

## Addendum 2 — Mid-call CRM lookup tool (Layer 2)

**Added 2026-09-08.** Layer 1 (call-start phone auto-fill) can miss — the caller rings from a
different number, or the business wants to look up by email/name. Layer 2 gives the agent a
**reusable mid-call lookup tool** it can call during the conversation, by **phone / email / name**,
using the SAME per-CRM presets.

### Requirements (addendum 2)
- Expose ONE tool to the LLM (e.g. `find_customer`) that takes `{ field: phone|email|name, value }`
  and looks the caller up in the agent's configured CRM, returning the matched record's fields.
- Reuse the per-CRM presets, **generalized** to `build_arguments(field, value)`:
  - **zoho_crm** `Search Records`: phone→`{phone}`, email→`{email}`, name→`{word}` (module Contacts).
  - **hubspot** `hubspot-search-objects`: phone→filter `phone CONTAINS_TOKEN`, email→filter `email EQ`,
    name→`{query}` (full-text).
  - **salesforce** `Query` SOQL: phone→`Phone LIKE '%digits%'`, email→`Email = '..'`, name→`Name LIKE '%..%'`.
- The LLM decides WHEN to call it — driven by **prompt guidance**: we inject a sensible default
  instruction ("if you don't know the caller, ask for their email or name and use find_customer"),
  and the agent builder can customize/override it in their own prompt.
- Only registered when the agent has CRM enrichment configured for a preset CRM; custom/other MCP
  behavior unchanged.
- Must not affect Layer 1: the call-start phone auto-fill, presets, config, and generic flow stay as-is.
- Field value the caller provides is a lookup key, NOT identity proof (verification = future Layer 3).

### Implementation Details (addendum 2)
- Generalize `CrmLookupPreset.build_arguments(phone)` → `build_arguments(field, value)` (field enum
  phone|email|name); Layer-1 enrich calls it with `field="phone"`. Keep `record_path` for response.
- Register the tool in the pipeline where MCP/custom tools are registered
  (`core/services/pipeline/builder/…` + `core/services/mcp_tool_service.py` area) so it joins the LLM's
  function set; the handler runs the preset build → `McpServerService.call_tool` → parse → return fields.
- Prompt guidance: a default snippet appended to the system prompt when the tool is active (one shared
  place, not per-agent copy); agent builder prompt can override.
- Reuse `get_crm_lookup_preset`, `McpServerService.call_tool`, `parse_tool_result`, `_resolve_path`.

### Acceptance Criteria (addendum 2)
- [ ] Agent can call `find_customer` mid-call by phone / email / name; the correct per-CRM request is built.
- [ ] Returned record fields are usable by the agent (same parsing/`record_path` as Layer 1).
- [ ] Tool is only offered when a preset CRM is configured; custom/other MCP unaffected.
- [ ] Default prompt guidance present; agent-builder prompt can override.
- [ ] No regression to Layer 1; tests added for `build_arguments(field, value)` across the 3 CRMs + the tool handler.
