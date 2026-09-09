# webhook-data-source-inbound

> feature: profile-variable-webhook · task: webhook-data-source-inbound

## Requirements

Build the per-agent webhook data source for profile variables, end to end, with inbound wired and outbound
supported in code (behavior deferred).

- Webhook config (one per agent): URL, GET/POST, custom headers (encrypted), phone-param key + location
  (query/body), directions, enabled.
- Per profile variable: `source` (static|webhook) + `source_path` (JSON dot-path).
- At call start (inbound), call the endpoint with the caller phone, parse JSON (list → first item), resolve
  paths, validate, and fill profile variables; fall back to each variable's default `value` on any failure.
- 3-second timeout; call always continues on inbound failure.
- Test-webhook endpoint + UI button showing raw response + per-path resolution.
- Outbound: code path present, failure behavior pluggable (abort-on-failure is deferred).

Non-goals: email/name identifiers, mid-call lookup tool, multiple webhooks per agent, the detailed outbound
abort flow.

## Implementation Details

- **Model:** new `AgentProfileWebhook` (`OrgScopedModel`, FK agent, CASCADE); add `source` + `source_path` to
  `AgentProfileVariable`. One Alembic migration for both.
- **Service:** new `AgentProfileWebhookService` — CRUD + validation + the async `httpx` call + response
  mapping/validation (reuse dot-path resolver pattern from the deleted `profile_crm_enrichment_service.py`) +
  `test()`. Encrypt/decrypt headers via `core/utils/encryption.py`; SSRF guard via `_assert_safe_url`.
- **API:** new `core/api/v1/agent_profile_webhook.py` (CRUD + `/test`); extend profile-variable schemas with
  `source`/`source_path`.
- **Runtime:** in `runner/pipecat.py`, after `load_profile_context`, fire the webhook (async task, 3s
  `wait_for`), merge into `profile_vars` filling only empty vars; mirror the deleted CRM merge semantics.
  Direction-aware behavior pluggable.
- **Frontend:** webhook config section in the Profile Variables drawer (reuse `HttpHeadersBuilder`,
  `SelectInput`, `TextInput`); per-variable source-path field in the modal; test button; types + service + query hooks.

## Acceptance Criteria

- [ ] Config + per-variable source_path round-trip via API (R1/R3).
- [ ] Inbound call fills variables from the webhook response; bad path caught by validation (R2/R4/R5).
- [ ] Failure/timeout falls back to default value; call continues; 3s cap (R6/R7).
- [ ] Outbound code path present with pluggable failure behavior (R8).
- [ ] Test webhook returns raw response + per-path resolution (R9).
- [ ] Headers encrypted at rest, never logged; SSRF guard; tests added; lint/typecheck pass.
