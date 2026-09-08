# profile-variables-crm-lookup — Requirements

When an agent has **profile variables** whose value is left empty (e.g. `username`, `age`) and a **CRM MCP
server** (HubSpot, Salesforce, etc.) is attached to that agent, the platform should look the caller up in
the CRM at the start of the call, pull their details, and use them to fill those empty variables before the
prompt is built. Today profile variables only read their stored DB value (empty → renders blank) and the
CRM is only reachable when the LLM chooses to call a tool mid-conversation; the two are entirely
disconnected. This feature adds the "glue": empty profile keys get enriched from the CRM at call start, on
the **prompt path only**.

## 1. Overview

- **Route(s) / entry points:**
  - Runtime: `core/services/pipeline/runner/pipecat.py` (per-call, where `load_profile_context` +
    `build_call_context` already run, ~lines 284–300).
  - Config API: profile-variables + a new field-mapping surface under the agent (backend
    `core/api/v1/agent_profile_variables.py` area; frontend Profile Variables screen).
- **Goal:** Personalize calls automatically — the agent knows the caller (name, age, etc.) from the CRM
  from the first second, without a mid-call tool round-trip and without manual per-caller data entry.
- **Scope:** Backend (new enrichment service + mapping storage + one runner call-site hook) and frontend
  (mapping UI in the Profile Variables screen). **Prompt path only.** Explicitly NOT changing the workflow
  engine (that path isn't wired for profile variables yet — out of scope here).
- **Shared / affected surfaces:** reuses existing MCP plumbing (`get_mcp_servers_for_agent`,
  `build_mcp_request_headers`, `resolve_server_url`, Pipecat `MCPClient`), the profile-variables service
  (`AgentProfileVariableService.get_variables_map`), and the prompt substitution engine
  (`build_call_context` / `substitute_variables`). No change to their public behavior for existing agents.

## 2. Involved Files

| File | Responsibility |
|------|----------------|
| `core/services/pipeline/runner/pipecat.py` | Call-start hook: after loading profile vars, enrich empty keys from CRM before `build_call_context`. |
| `core/services/agents/profile_context.py` | Shared loader; likely the home (or caller) of the new enrichment step so prompt + future workflow paths stay in sync. |
| `core/services/agents/` (new) e.g. `profile_crm_enrichment_service.py` | New service: given caller identity + mapping + attached CRM, call the lookup tool, map fields → empty keys. |
| `core/services/mcp_tool_service.py` | Reused: `get_mcp_servers_for_agent`, `build_mcp_request_headers`, `resolve_server_url`, tool discovery/invocation (direct, not via LLM). |
| `core/models/agent_profile_variable.py` (or new mapping model) | Stores the CRM field mapping + which lookup tool is chosen. |
| `core/api/v1/agent_profile_variables.py` (+ mcp discovery route) | Endpoints to read/write the mapping and to list CRM tool/fields for auto-suggest. |
| `alembic/versions/*` | Migration for the mapping storage. |
| `frontend/src/components/agents/profile-variables/*` | Mapping UI: per-variable CRM-field dropdown + lookup-tool confirm. |
| `frontend/src/lib/api/agentProfileVariables.ts`, `frontend/src/services/agentProfileVariableService.ts`, `frontend/src/types/agentProfileVariable.ts` | HTTP hooks/service/types for the mapping. |

## 7. Behavior & Functionality

- **Match key — phone.** Caller is matched in the CRM by **phone number** (`call_data["from"]`, always
  available on a call). Email may be an optional later fallback — not required now.
- **Which variables get filled — empty only.** Only profile variables whose stored value is empty are
  enriched. A value the user typed is always respected and never overwritten by the CRM.
- **The mapping — user-configured, auto-suggested.** The agent builder (org user, in the dashboard — NOT a
  developer, NOT the caller) maps each variable to a CRM field via a dropdown in the Profile Variables
  screen. The system auto-suggests the obvious match by name (e.g. `age`→`age`); the user can change it
  (e.g. `username`→`first_name`). Saved once per **agent**.
- **The lookup tool — auto-detect, user-confirm.** The system scans the attached CRM MCP's tool list and
  auto-suggests the likely "find/search contact by phone" tool; the user confirms or picks the right one.
  Not silently auto-picked.
- **No CRM match → default, else blank; never fail the call.** If the CRM returns no match (or errors, or
  times out), each unfilled variable falls back to its inline default (`{{username|there}}`) if present,
  else renders blank. The call proceeds normally — enrichment failure must never block or crash the call.
- **APIs & data model:** new/extended endpoints (org-scoped, `require_org_member`) to (a) GET the CRM
  tool + fields for auto-suggest, (b) GET/PUT the per-agent mapping + chosen lookup tool. New storage for
  the mapping (column(s)/JSON on the profile variable row, or a small mapping model) + Alembic migration.
  Tenancy: everything scoped to the agent's org. CRM auth reuses the org's single stored (encrypted) MCP
  token — no per-caller token.
- **Error handling:** enrichment runs in a guarded, timed-out step (mirrors the existing
  `load_profile_context` degrade-to-empty pattern); any failure logs a full traceback via
  `logger.exception` and degrades to the default/blank behavior above.

## 8. Non-Functional Requirements

- **Standards compliance:** logic in a `BaseService` (not the runner/router); reuse existing MCP + profile
  helpers, do not duplicate; every `except` logs a full traceback; secrets stay encrypted and unlogged.
- **Performance:** the CRM lookup happens before the greeting — it must be bounded by a timeout and must
  not block the event loop (run the sync/DB and MCP work off the loop, like the existing profile-var load).
- **Security:** org-scoped queries only (no IDOR); CRM token never logged; caller phone treated as call data.
- **Observability:** log enrichment start/outcome with the call `trace_id` and a context tag; record which
  keys were filled vs. left to default/blank.

## 9. Acceptance Criteria

- [ ] With a CRM attached, a mapping configured, and a caller present in the CRM, empty profile variables
      are filled from the CRM and appear substituted in the prompt (R: match-by-phone, empty-only, mapping).
- [ ] A profile variable with a user-set value is never overwritten by the CRM (empty-only).
- [ ] No CRM match / CRM error / timeout → variable falls back to its default (`{{k|default}}`) or blank,
      and the call still connects and runs (never fails).
- [ ] The Profile Variables screen lets the user map each variable to a CRM field (auto-suggested) and
      confirm the auto-detected lookup tool; the mapping persists per agent.
- [ ] Enrichment errors are logged with a traceback and the CRM token is never logged.
- [ ] Backend logic lives in a service and reuses existing MCP/profile helpers; migration is safe; tests
      added; lint + typecheck pass.

## 10. Out of Scope

- The **workflow-engine** path (`{{profile.<key>}}` in workflow nodes) — not wired for profile variables
  yet; enrichment there is a separate task.
- Per-caller / per-end-user CRM tokens (auth stays the org's single stored token).
- Email or other match keys beyond phone (possible later fallback).
- Writing back to the CRM; caching CRM results across calls.
