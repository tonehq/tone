# Agents — Edit Flow (E2E scenarios)

> Companion to `frontend/e2e/dashboard/agents-edit.spec.ts`. Each scenario ID
> below maps to a Playwright `test(...)` name so a failing run can be triaged
> directly back to a scenario.

## User stories

- As a user, I can open `/agents/edit/{type}/{id}` and see the existing
  configuration pre-filled across all six steps.
- I can change any field and save — only the changed fields are sent to the
  backend.
- I can upload KB documents and assign phone numbers from sub-modals.
- I can delete the agent from the header.
- If I try to navigate away with unsaved changes, a custom modal asks me to
  discard or keep editing — covering sidebar nav, browser back, header Back,
  "New tool" / "New MCP server" buttons.
- If the agent ID is not found (404), the page redirects me back to the agent
  list with a toast.

> **Routing update (focused editor):** The editor is now a focused full-screen
> experience (the main app sidebar is hidden) and each section is its own URL
> route. Opening an agent lands on its **Overview** first; the configuration
> steps live at `/agents/edit/{type}/{id}/{section}` where section ∈
> `overview | basics | prompt | ai | voice | tools | knowledge`. The bare
> `/agents/edit/{type}/{id}` redirects to `…/overview`. Section navigation is
> route-based (rail `<Link>`s), so it does **not** trigger the unsaved-changes
> guard; only leaving the editor does.

## Routes

| Route | Renders |
|---|---|
| `/agents/edit/{type}/{id}` | redirect → `/agents/edit/{type}/{id}/overview` |
| `/agents/edit/{type}/{id}/overview` | `AgentOverview` (Vercel-style detail card) |
| `/agents/edit/{type}/{id}/{section}` | the matching step (Basics/Prompt/AI/Voice/Tools/Knowledge) |

The form state + chrome (header save-bar, rail, modals) live in
`agents/edit/[type]/[id]/layout.tsx` → `AgentEditorShell`, which persists across
section navigation so values are never lost.

## Key files

- `src/components/agents/AgentEditorShell.tsx`
- `src/components/agents/agent-form/steps/{KnowledgeBaseUploadModal,AssignPhoneNumberModal}.tsx`
- `src/hooks/useUnsavedChangesGuard.ts`
- `src/utils/agentFormUtils.ts` — `agentDetailToFormState`, `formStateToUpdatePayload`
- `src/services/agentsService.ts` — `getAgent`, `updateAgent`, `deleteAgent`
- `src/atoms/AgentsAtom.tsx` — `fetchAgentAtom`, `updateAgentAtom`, `deleteAgentAtom`

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| GET | `/agent/get_agent?agent_id=` | Page mount |
| PUT | `/agent/update_agent?agent_id=` | Save (diff payload) |
| DELETE | `/agent/delete_agent?agent_id=` | Confirm delete |
| POST | `/knowledge-base/upload` (FormData with `agent_id`) | KB upload modal |
| GET | `/channel/{id}/phone_numbers` | Phone assign modal |

## Scenarios — Edit (AE-001 … AE-022)

### Hydration

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-001 | Visit `/agents/edit/inbound/{id}` | `GET /agent/get_agent` fires once; form hydrates via `agentDetailToFormState` | `loads the agent and hydrates the form` |
| AE-002 | Switch between tabs after hydrate | All step fields show fetched values; tab switches don't reset state | `step values persist across tab switches` |
| AE-003 | `GET /agent/get_agent` returns 404 | Toast "Agent not found"; `router.replace('/agents')`; URL not in history | `404 redirects to /agents` |
| AE-004 | `GET /agent/get_agent` returns 500 | `handleApiError` toast; user stays on page | `500 surfaces an error toast` |

### Header & meta

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-005 | Header on edit | Shows agent name, avatar initial, **Delete** button visible, no "New" badge | `header shows Delete and the agent name` |
| AE-006 | Save button label | Reads "Save changes" (not "Create agent") | `Save button reads Save changes on edit` |

### Diff-aware update

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-007 | Change only `name` and save | `PUT /agent/update_agent` payload is exactly `{name: '…'}` | `name-only change posts diff payload` |
| AE-008 | Save without any change | Toast "No changes" + skips API call | `unchanged save shows No changes toast` |
| AE-009 | Toggle one tool and save | Payload is `{tool_ids: [...]}` only | `tool toggle posts tool_ids diff only` |
| AE-010 | Clear description then save | Payload includes `{description: null}` (uses `exclude_unset`) | `clearing description posts null` |

### Sub-modals

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-011 | Upload a KB file | `POST /knowledge-base/upload` with FormData (`agent_id` + file); modal closes; new upload auto-selected in the picker | `KB upload modal posts file and selects on close` |
| AE-012 | Assign a phone number | After save, form re-hydrates with `channel_id` and `label` round-tripped from backend | `phone assignment round-trips channel_id and label` |
| AE-013 | Open Preview after edits | ReviewStep modal reflects live form values via `useWatch` | `Preview shows live form state` |

### Delete

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-014 | Click Delete | Confirmation modal opens with destructive copy | `Delete opens confirmation modal` |
| AE-015 | Confirm delete | `DELETE /agent/delete_agent?agent_id=` fires; redirect to `/agents`; **no** unsaved-changes prompt even if form is dirty | `Delete bypasses unsaved-changes guard and redirects` |

### Unsaved-changes guard (critical regression area)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-016 | Dirty + click sidebar Link | Custom modal "Discard unsaved changes?" appears; navigation blocked until decision | `dirty sidebar click opens the discard modal` |
| AE-017 | Dirty + browser back | Custom modal appears; "Keep editing" cancels and stays on form; "Discard" runs the back | `dirty browser back routes through the discard modal` |
| AE-018 | Dirty + reload | Native `beforeunload` dialog (not custom — the platform forbids replacing it) | `dirty reload triggers beforeunload` |
| AE-019 | Dirty + click "New tool" button | Custom modal appears; Discard → navigates to `/tools/create` | `dirty New tool click routes through discard modal` |
| AE-020 | Dirty + click header Back arrow | Custom modal appears | `dirty header Back routes through discard modal` |
| AE-021 | Clean state + any nav path | No modal; navigation proceeds | `clean state never opens the discard modal` |
| AE-022 | Save then click sidebar | Form is no longer dirty after `methods.reset`; nav proceeds immediately | `successful save resets dirty so nav is unblocked` |

### Comprehensive flow (every field, every step)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AE-FULL | Create a throw-away inbound agent, change **every** writable control across Basics, Prompt, AI, and Voice, save, reload, verify each value persisted, then delete | All filled values rehydrate after reload; agent is deleted in the same test for cleanup | `modifies every step, saves, reloads and verifies` |

AE-FULL is a edit-mode mirror of `AC-FULL` for the steps that don't depend on org catalog setup (KB, phone numbers, tools, MCP are intentionally excluded so the spec works against any seeded org).

| Step | Field | Path | Helper | Asserted on reload |
|---|---|---|---|---|
| Basics | Description | `description` | `fillBasicsStep({ description })` | yes |
| Basics | First message | `config.first_message` | `fillBasicsStep({ firstMessage })` | yes |
| Basics | End call message | `config.end_call_message` | `fillBasicsStep({ endCallMessage })` | yes |
| Basics | Active toggle | `is_active` | `fillBasicsStep({ toggleActive: true })` | — (visual) |
| Prompt | System prompt | `config.system_prompt_template` | `fillPromptStep({ systemPrompt })` | yes |
| AI | LLM provider | `config.llm_settings.provider_id` | `fillAiStep()` | — (catalog-dependent) |
| AI | LLM model | `config.llm_settings.model_id` | `fillAiStep()` | — (catalog-dependent) |
| AI | Temperature (slider) | `config.llm_settings.temperature` | `fillAiStep({ temperatureSteps })` | — |
| AI | Max tokens | `config.llm_settings.max_tokens` | `fillAiStep({ maxTokens })` | yes |
| AI | Conversation history token limit | `config.conversation_history_token_limit` | `fillAiStep({ tokenLimit })` | yes |
| Voice (TTS) | Language | `config.voice_settings.language` | `fillVoiceStep()` | — |
| Voice (TTS) | Provider | `config.voice_settings.provider_id` | `fillVoiceStep()` | — |
| Voice (TTS) | Model | `config.voice_settings.model_id` | `fillVoiceStep()` | — |
| Voice (TTS) | Voice | `config.voice_settings.voice_id` | `fillVoiceStep()` | — |
| Voice (TTS) | Speed (slider) | `config.voice_settings.speed` | `fillVoiceStep()` via `setSliderByKeyboard` | — |
| Voice (STT) | Provider | `config.stt_settings.provider_id` | `fillVoiceStep()` | — |
| Voice (STT) | Model | `config.stt_settings.model` | `fillVoiceStep()` | — |

Notes:

- AE-FULL uses a freshly created agent (not the shared `fixtureAgentId`) so the assertions can re-read only this test's writes.
- The temperature and speed sliders are driven via Radix keyboard semantics (`Home` then `N × ArrowRight`); the same number of presses yields the same value across environments.
- Tools, MCP, KB documents, and phone numbers are exercised in **`AC-FULL`** (create mode) and not in AE-FULL. Edit-mode coverage for those modals is still tracked by AE-009 (tools), AE-011 (KB upload), and AE-012 (phone assignment).

## Edge cases

- Backend dropping `selected_tools` from `agent_mcp_server` (legacy column) →
  payload silently omits it; covered indirectly by AE-009.
- `agent_response` returning `phone_numbers` without `channel_id` is a
  regression that AE-012 explicitly guards against.
- `update_agent` honouring explicit `null` via `exclude_unset=True` is covered
  by AE-010 — if this flips to `exclude_none`, AE-010 fails.

## Coverage map (which scenarios `AE-FULL` transitively exercises)

| Scenario | Transitively covered by AE-FULL? | Notes |
|---|---|---|
| AE-002 Step values persist across tabs | yes | every step is visited and its values are re-asserted after reload |
| AE-007 Diff-aware name update | partially | save round-trip is exercised, but the test changes many fields, not just `name` |
| AE-010 Clearing description posts null | no | AE-FULL only sets non-empty values |

Scenarios still tracked only by their individual `test.fixme` placeholders (AE-004 500-error toast, AE-009 tool diff, AE-010 description null, AE-011 KB upload, AE-012 phone round-trip, AE-013 Preview live form, AE-017 dirty back, AE-018 dirty reload, AE-022 save resets dirty) are *not* exercised by AE-FULL.

## Out of scope (covered elsewhere)

- Initial creation flow → `agents-create.md`.
- Listing / search / sort → `agents.md`.
- Backend integrity tests → pytest under `test-cases/`.

## Cleanup

Tests create a "fixture" agent in `beforeAll` and `DELETE` it in `afterAll`
via `/agent/delete_agent`. If the spec aborts before cleanup, the next run
sweeps any agent name starting with `__e2e__` from `/agent/list`.
