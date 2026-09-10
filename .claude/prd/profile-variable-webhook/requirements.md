# Profile Variable Webhook — Requirements

A per-agent **webhook data source** for profile variables. At call start, Tone calls a user-configured HTTP
endpoint (URL + GET/POST + custom headers, Postman-style), sends the caller's phone number, parses the JSON
response, maps configured JSON paths into the agent's profile variables, validates them, and injects the
resolved values into the system prompt. This is the generic replacement for the CRM-lookup subsystem that was
removed on the `revert-crm-profile-variables` branch (the old `AgentProfileCrmConfig` + `ProfileCrmEnrichmentService`
+ `find_customer` tool) — same call-start seam, but driven by an arbitrary user HTTP endpoint instead of an MCP tool.
Inbound calls are wired first; the code is built to support outbound too (different execution point + failure
behavior), which is deferred for detailed design.

## 1. Overview

- **Route(s) / entry points:**
  - Backend config API: `CRUD /agents/{agent_id}/profile-webhook` + `POST /agents/{agent_id}/profile-webhook/test`
  - Runtime hook: `core/services/pipeline/runner/pipecat.py` (call-start, after static profile vars load, before prompt build)
  - Frontend: Profile Variables drawer (`ProfileVariablesDrawer` / `ProfileVariablesManager`) in the agent editor Prompt step
- **Goal:** let a customer dynamically populate profile variables from their own HTTP endpoint at call start, so
  the agent's prompt is personalized per caller without Tone integrating each CRM directly.
- **Scope:** Backend (new model + migration + service + API + call-start enrichment + HTTP client), Frontend
  (webhook config UI + per-variable source-path field + test button). **Not changing:** the static
  `{key, value, description}` profile-variable behavior — webhook is additive; static `value` becomes the fallback.
- **Shared / affected surfaces:** `AgentProfileVariable` model/service/API; `profile_context.py`; the runner's
  call-start prompt-context assembly; the Profile Variables UI; reuses `HttpHeadersBuilder`, `SelectInput`,
  `TextInput`, and `core/utils/encryption.py`.

## 2. Involved Files

| File | Responsibility |
|------|----------------|
| `core/models/agent_profile_webhook.py` (new) | Per-agent webhook config model (URL, method, headers, phone-param, directions, enabled) |
| `core/models/agent_profile_variable.py` | Add `source` discriminator + `source_path` (JSON path) columns |
| `alembic/versions/*_add_profile_variable_webhook.py` (new) | Create webhook table + add variable columns |
| `core/services/agents/agent_profile_webhook_service.py` (new) | CRUD + validation + the webhook HTTP call + response mapping/validation + test |
| `core/services/agents/agent_profile_variable_service.py` | Carry `source`/`source_path` through create/update/list |
| `core/api/v1/agent_profile_webhook.py` (new) | Config CRUD + test endpoints |
| `core/api/v1/agent_profile_variables.py` | Add `source`/`source_path` to request/response schemas |
| `core/services/agents/profile_context.py` | Load webhook plan + provide the enrichment entry point |
| `core/services/pipeline/runner/pipecat.py` | Fire the webhook at call start, merge results into `profile_vars` |
| `core/services/agents/errors.py` | Webhook config/validation error types |
| `frontend/src/components/agents/profile-variables/*` | Webhook config form + per-variable source-path field + test button |
| `frontend/src/types/agentProfileVariable.ts`, `frontend/src/services/*`, `frontend/src/lib/api/*` | Types + HTTP service + query hooks for the webhook config |

## 3. Layout & Structure *(UI)*

- Webhook configuration lives inside the existing **Profile Variables drawer** (opened from the Prompt step),
  as a dedicated section above/beside the variables table: URL field, method dropdown (GET/POST), phone-param
  key + location (query vs body), custom headers (key-value list), an **enabled** toggle, a **directions**
  selector (inbound / outbound), and a **Test webhook** button that shows the raw response + which configured
  paths resolved.
- Each profile variable row gains an optional **source path** field (e.g. `properties.name`) in the
  add/edit modal; a variable with a source path is webhook-filled, otherwise it is static.

## 4. Content & Copy *(UI — minimal)*

- Section title: "Webhook data source"; helper: "Call your endpoint at call start and fill profile variables from the response."
- Per-variable field label: "Source path (JSON)"; helper example: `properties.name` or `data.customer.tier`.
- Test result: show HTTP status, pretty JSON, and per-path ✓/✗ resolution.

## 7. Behavior & Functionality

- **R1 — Config shape (one per agent):** a single webhook config per agent with: `endpoint_url`, `http_method`
  (`GET`|`POST`), `headers` (list of key-value pairs, stored encrypted at rest), `phone_param_name` (user-chosen
  key), `phone_param_location` (`query`|`body`), `directions` (which of inbound/outbound it runs for),
  `is_enabled`.
- **R2 — Request:** on a qualifying call, send the caller's phone under `phone_param_name` in the chosen location
  (query for GET / body for POST). Inbound caller = `from_number`; outbound caller = `to_number`. v1 sends phone
  only; design leaves room to add email/name later.
- **R3 — Variable source mapping:** each `AgentProfileVariable` gains `source` (`static`|`webhook`) and
  `source_path` (dot-path into the response, e.g. `properties.name`). The variable's `key` is the prompt token
  (`{{profile.<key>}}`); `source_path` is where the value is read from. They are independent.
- **R4 — Response parsing:** parse JSON; if the response is a **list**, take the **first item**; then resolve
  each webhook-variable's `source_path` against it (dot-path descent, reusing the old CRM `_resolve_path`/`_descend` logic).
- **R5 — Validation:** validate HTTP status and that each configured `source_path` resolves to a usable scalar
  (Pydantic-backed check on the extracted flat dict). A path that doesn't resolve = validation failure for that variable.
- **R6 — Fallback (inbound):** on any failure (timeout, non-2xx, bad/missing path, parse error), fall back to
  the variable's existing `value` (its default). The call **always continues**. Never overwrite a configured
  static value with an empty webhook result.
- **R7 — Timeout:** hard **3-second** cap on the webhook request; slower than that → use defaults.
- **R8 — Outbound (built now, behavior deferred):** code supports outbound; the planned behavior is to run the
  webhook **before the call is placed** and **abort the call on failure** — but the exact outbound abort flow is
  deferred to a later discussion. Failure behavior is **per-direction** (graceful for inbound, abort for outbound)
  and must be pluggable, not hardcoded.
- **R9 — Test webhook:** a config-time endpoint/button calls the user's endpoint with a sample/real phone and
  returns the raw response plus per-path resolution, so misconfigurations (e.g. `name` vs `properties.name`) are
  caught before going live.
- **APIs & data model:** see §2; new `agent_profile_webhooks` table + two new columns on `agent_profile_variables`.
  All org-scoped, `require_org_member`, agent-in-org checks as in the existing profile-variable routes.
- **Error handling:** config validation errors → 400/409 with structured codes; runtime webhook failures are
  logged (full traceback, context-tagged, phone/response never logged) and degrade per R6.

## 8. Non-Functional Requirements

- **Standards compliance:** logic in services (not routers); reuse existing shared helpers; `logger.exception`
  in every except; lint/typecheck/tests pass.
- **Performance:** webhook runs as an async task overlapping call setup; 3s cap; AES encrypt/decrypt of headers
  is microseconds (no measurable call-start latency). Non-blocking DB read via executor as today.
- **Security:** headers encrypted at rest (`core/utils/encryption.py`), decrypted only just before the request,
  never logged; SSRF guard on the user URL (reuse `_assert_safe_url` from `custom_tool_service.py`); org-scoped access.
- **Observability:** context-tagged logs (`[profile-webhook]`), correlate by `trace_id`; log success/failure and
  which paths resolved (never values).

## 9. Acceptance Criteria

- [ ] R1/R3 — A webhook config and per-variable `source_path` can be saved against an agent and round-trip via the API.
- [ ] R2/R4/R5 — On an inbound call, the webhook is called with the caller phone, the JSON (object or list) is
      parsed, paths resolve, and validation catches a bad path.
- [ ] R6/R7 — On timeout/error/bad path, the variable falls back to its default `value` and the call continues; 3s cap enforced.
- [ ] R8 — Direction-aware failure behavior is pluggable; outbound path exists (behavior stub OK pending later design).
- [ ] R9 — The Test webhook action returns raw response + per-path resolution in the UI.
- [ ] Headers are encrypted at rest and never appear in logs; SSRF guard applied.
- [ ] Tests added (service + mapping/validation + call-start merge); lint + typecheck pass.

## 10. Out of Scope

- Sending email/name as request identifiers (designed-for, not built in v1).
- Mid-call LLM-callable lookup tool (the old Layer-2 `find_customer`) — not part of this feature.
- Detailed outbound "abort the call on failure" flow — deferred to a later discussion.
- Multiple webhook configs per agent; non-JSON responses; auth flows beyond static headers.
