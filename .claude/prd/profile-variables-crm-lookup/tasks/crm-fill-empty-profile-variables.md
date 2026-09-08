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
