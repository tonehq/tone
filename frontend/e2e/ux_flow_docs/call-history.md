# Feature Doc: Call History

Feature documentation for the Call History list + per-call detail pages. Used
by `/generate-tests call-history` (or `--docs e2e/ux_flow_docs/call-history.md`) to
ensure all user cases are covered.

Call History is the historical record of voice calls handled by the agent
pipeline. Each call has metadata, a recording, a transcript, and metrics. The
list page supports rich filtering; the detail page splits into three tabs
(Transcription & Recordings, Metrics, Call Configurations).

---

## Pages

- **Routes**:
  - `/call-history` — list view
  - `/call-history/[callId]` — redirects to `…/transcription`
  - `/call-history/[callId]/transcription` — Transcription & Recordings tab
  - `/call-history/[callId]/metrics` — Metrics tab
  - `/call-history/[callId]/configurations` — Call Configurations tab
- **Wrappers**: `src/app/(dashboard)/call-history/page.tsx` (+ nested `[callId]/...`)
- **Main components**:
  - `src/components/call-history/CallHistory.tsx`
  - `src/components/call-history/CallHistoryFilterDrawer.tsx`
  - `src/components/call-history/CallDetailShell.tsx`
  - `src/components/call-history/CallSummaryCard.tsx`
  - `src/components/call-history/sections/TranscriptionRecordingsSection.tsx`
  - `src/components/call-history/sections/MetricsSection.tsx`
  - `src/components/call-history/sections/CallConfigurationsSection.tsx`
  - `src/components/call-history/CallDetailContext.tsx`
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fcall-history` without `tone_access_token` cookie)

---

## User Stories

### US-1: Browse and filter calls

**As an** operator, **I want to** see a paginated list of recent calls with
search and filters, **so that** I can locate the calls I care about.

**Acceptance criteria**:

- [ ] Page header shows "Call History" + total-call badge (Phone icon)
- [ ] Token search bar placeholder: "Filter by field… (e.g. status:completed)"
- [ ] "Columns" button (Columns3 icon) opens a popover with Call History + Call Metrics groups; supports group toggles, individual toggles, Reset + Apply; badge shows hidden count
- [ ] "Filters" button (SlidersHorizontal icon) shows a badge for the drawer's filter count (not toolbar status/agent)
- [ ] Table renders the Agent column sticky-left with `AgentTypeBadge`
- [ ] Pagination supports page sizes 10, 25, 50, 100; page resets to 1 on filter/sort/page-size change

### US-2: Filter via the drawer

**As an** operator, **I want to** narrow results by time range, facets,
turns, and latency, **so that** I can isolate specific calls.

**Acceptance criteria**:

- [ ] Filter drawer is a right-side panel titled "Filters" with description "Narrow call history by time, status, agent, pipeline and metrics."
- [ ] Collapsible sections: Timeline (DateRangePicker), facet sections (direction, channel_type, models, etc.), Turns (From/To number inputs, min 0), Avg latency (slider 0–10 s, step 0.1 s)
- [ ] Helper text under Turns: "Calls with no metrics record are excluded when this range is set."
- [ ] Footer: "Reset" (disabled when no filters set) and "Apply"
- [ ] Closing the drawer without "Apply" reverts the draft to the last applied state
- [ ] Browser time zone is captured via `getBrowserTimeZone` and sent with the filters

### US-3: Open a call detail page

**As an** agent owner, **I want to** click a row and review the call,
**so that** I can QA conversations.

**Acceptance criteria**:

- [ ] Clicking a row navigates to `/call-history/[callId]/transcription`
- [ ] Desktop layout: left sidebar rail (SidebarShell) with "Back to Call History" link and three tabs (Transcription & Recordings, Metrics, Call Configurations)
- [ ] Mobile layout: top bar with back arrow + horizontally scrollable tab pills
- [ ] Page header: breadcrumb "Call History / <Agent Name>" + title + truncated call-id pill (tooltip shows full id) + "Copy link" button (turns into "Copied" with check icon for 1.5 s)
- [ ] Sticky `CallSummaryCard` shows chips: agent type, status badge, duration, From/To phones, channel type, start/end times

### US-4: Listen and follow along on Transcription tab

**As an** agent owner, **I want to** play audio and search the transcript,
**so that** I can find a specific moment.

**Acceptance criteria**:

- [ ] "Audio Recording" h3 + native HTML `<audio>` player when an audio URL is available
- [ ] Loading state: "Loading audio…" with spinner
- [ ] Audio fetch error: "Failed to load audio"
- [ ] No recording at all: "No audio recording available"
- [ ] "Transcription" h3 + search input placeholder "Search transcription…"
- [ ] Messages render chat-style: user left-aligned with muted background, assistant right-aligned with primary background
- [ ] Each message displays role (User/Assistant), text, and timestamp
- [ ] Search highlights are case-insensitive (regex-escaped) and rendered as yellow `<mark>` runs
- [ ] No transcript: "No transcription available"; search with no matches: "No matching messages"

### US-5: Inspect Metrics tab

**As an** analyst, **I want to** see per-call charts of latency, tokens, and
TTS usage, **so that** I can monitor cost and quality.

**Acceptance criteria**:

- [ ] Charts include: latency per turn, LLM tokens by model, TTS chars by model, TTFB by model, processing times, end-to-end latency
- [ ] Each chart supports a Chart ↔ Table toggle
- [ ] StatCards show aggregate values
- [ ] Charts handle empty data gracefully (no crash, friendly empty state)

### US-6: Review Configurations tab

**As a** tester, **I want to** see the call's metadata and the agent config
at call time, **so that** I can reproduce the test.

**Acceptance criteria**:

- [ ] Section lists agent name, direction, status, started_at, ended_at, channel_type, recording_upload_id, and other call metadata
- [ ] Values render with consistent labels and humanized timestamps

---

## User Workflow Steps

Step-by-step expected user behavior per major story. Used to drive
Playwright spec generation under `frontend/e2e/dashboard/call-history.spec.ts`.

**WF-1: Browse + filter calls** (positive)
1. User signs in (worker fixture `loginViaUI`) → expected: lands on `/home`
2. User clicks sidebar `Call History` link → expected: URL is `/call-history`; `POST /call-log/list` and `POST /call-log/facets` fire with `start_date_time`, `end_date_time`, current browser tz
3. User sees h1 "Call History" + Phone badge with total → expected: badge text matches `data.total`
4. User types `status:completed` in the token search → expected: filters payload includes `{field: "status", operator: "in", value: ["completed"]}`; table refetches; page resets to 1
5. User changes page size to 25 → expected: `page_size: 25`, page resets to 1
6. User clicks a row → expected: `router.push('/call-history/<id>')` → server redirect to `/call-history/<id>/transcription`

**WF-2: Use the Filters drawer** (positive)
1. User clicks "Filters" button → expected: right drawer titled "Filters" opens, description "Narrow call history by time, status, agent, pipeline and metrics."
2. User expands Timeline, picks a 7-day range → expected: draft state updates; list NOT yet refetched
3. User toggles a facet value (e.g. `direction: outbound`) → expected: chip appears in drawer count
4. User enters Turns `From=5, To=20` → expected: helper text visible "Calls with no metrics record are excluded when this range is set."
5. User drags Avg latency to `0.5s — 3.2s` → expected: slider label updates live
6. User clicks "Apply" → expected: drawer closes; `POST /call-log/list` fires with new filters; "Filters" toolbar button shows badge count `> 0`
7. User reopens drawer, clicks "Reset" → expected: draft cleared; Reset becomes disabled (no active filters)
8. User closes drawer via Esc / overlay click WITHOUT Apply → expected: draft discarded; applied filters unchanged

**WF-3: Open detail + tabs** (positive)
1. User clicks row for call X → expected: `/call-history/X/transcription`; `GET /call-log/X` fires; `CallSummaryCard` renders chips
2. User clicks "Metrics" sidebar tab → expected: URL `/call-history/X/metrics`; no second `GET /call-log/X` (shared context)
3. User clicks "Call Configurations" → expected: URL `/call-history/X/configurations`; section lists agent_name, direction, status, channel_type, started_at, ended_at
4. User clicks "Back to Call History" rail link → expected: URL `/call-history`; list state preserved

**WF-4: Audio playback + transcript search** (positive)
1. User on `/transcription` tab; call has `recording_upload_id` → expected: `GET /call-log/X/audio-url` fires; spinner "Loading audio..." shows
2. Response returns `audio_url` → expected: native `<audio controls>` renders with `src=audio_url`
3. User types `"reschedule"` in transcript search → expected: only matching messages remain; matched substring wrapped in `<mark class="bg-yellow-200">`
4. User clears search → expected: full transcript restored

**WF-5: Copy link** (positive)
1. User clicks "Copy link" → expected: `navigator.clipboard.writeText(window.location.href)` fires; button label flips to "Copied" with Check icon
2. After ~1.5s → expected: button reverts to "Copy link"

---

## Input Specifications

### Filter drawer

| Field        | Type         | Required | Validation Rules                              | Exact Error Message |
| ------------ | ------------ | -------- | --------------------------------------------- | ------------------- |
| Timeline     | DateRangePicker (start + end + tz) | No | end >= start; both ISO-8601; tz from `getBrowserTimeZone()` | (no inline error; range picker disables invalid days) |
| Facet toggle | Checkbox     | No       | enum value drawn from `POST /call-log/facets` | n/a                 |
| Turns — From | number       | No       | integer, `>= 0`; HTML `min=0`                 | (no inline error; sub-zero blocked by browser) |
| Turns — To   | number       | No       | integer, `>= 0`; recommend `>= From` (not enforced) | n/a            |
| Avg latency  | Slider [min,max] | No   | bounds `0.0–10.0`, step `0.1`; min auto-snapped below max | n/a       |

### Token search (toolbar)

| Field            | Type   | Required | Validation Rules                       | Exact Error Message |
| ---------------- | ------ | -------- | -------------------------------------- | ------------------- |
| Token search bar | TokenSearchBar | No | `field:value` syntax; field must match `DRAWER_FACET_SECTIONS` keys; value autocompletes from `GET /call-log/filter-values` | (invalid tokens silently ignored) |

### Transcript search

| Field   | Type   | Required | Validation Rules                          | Exact Error Message |
| ------- | ------ | -------- | ----------------------------------------- | ------------------- |
| Search  | text   | No       | case-insensitive substring; regex-escaped via `escapeRegex` | (no inline error; empty match shows "No matching messages") |

---

## Success Scenarios

**PS-1: List loads with default range**
- Preconditions: signed-in user; calls exist in DB.
- Steps: navigate to `/call-history`.
- Expected: h1 "Call History", Phone badge shows `total`, first page of rows visible, Agent column sticky-left.
- **Mock API**: `POST /call-log/list` →
  ```json
  {
    "items": [
      {
        "id": "call-uuid",
        "agent_id": "agent-uuid",
        "agent_name": "Concierge",
        "from_number": "+14155550100",
        "to_number": "+14155550199",
        "status": "completed",
        "duration_seconds": 132,
        "started_at": "2026-05-15T10:00:00+00:00",
        "ended_at": "2026-05-15T10:02:12+00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
  ```

**PS-2: Apply Status=completed via token search**
- Preconditions: PS-1 succeeded; at least one completed call exists.
- Steps: type `status:completed` token; press Enter.
- Expected: refetch fires; page resets to 1; row count matches filtered total.
- **Mock API**: `POST /call-log/list` request body contains `filters: [{field: "status", operator: "in", value: ["completed"]}]`; response shape same as PS-1.

**PS-3: Open call detail**
- Preconditions: PS-1 row visible.
- Steps: click any row.
- Expected: URL `/call-history/<id>/transcription`; breadcrumb "Call History / <Agent Name>"; `CallIdPill` shows truncated id; tooltip shows full id.
- **Mock API**: `GET /call-log/<id>` →
  ```json
  {
    "id": "call-uuid",
    "agent_id": "agent-uuid",
    "agent_name": "Concierge",
    "from_number": "+14155550100",
    "to_number": "+14155550199",
    "status": "completed",
    "duration_seconds": 132,
    "recording_upload_id": "rec-uuid",
    "transcript": [
      {"role": "assistant", "text": "Hi, how can I help?", "timestamp": "2026-05-15T10:00:01+00:00"},
      {"role": "user", "text": "I need to reschedule.", "timestamp": "2026-05-15T10:00:05+00:00"}
    ]
  }
  ```

**PS-4: Audio loads + plays**
- Preconditions: PS-3; call has `recording_upload_id`.
- Steps: wait for audio player to mount.
- Expected: "Loading audio..." spinner appears briefly; then `<audio controls>` with the signed URL.
- **Mock API**: `GET /call-log/<id>/audio-url` → `{"audio_url": "https://r2.example.com/calls/call-uuid.mp3?signature=..."}`

**PS-5: Transcript search highlights**
- Preconditions: PS-3 transcript loaded.
- Steps: type `reschedule` in transcript search.
- Expected: only matching message visible; substring wrapped in `<mark class="bg-yellow-200">`.

**PS-6: Copy link succeeds**
- Preconditions: PS-3.
- Steps: click "Copy link".
- Expected: clipboard contains `window.location.href`; button reads "Copied" with Check icon for ~1.5s, then reverts to "Copy link".

**PS-7: Apply drawer filter + reset**
- Preconditions: PS-1.
- Steps: open drawer → toggle `direction: outbound` → Apply → reopen → Reset.
- Expected: list refetches twice; after Apply, "Filters" toolbar button badge count = 1; after Reset, badge gone and Reset is disabled.

---

## Failure Scenarios

**FS-1: List fetch fails (500)**
- Preconditions: signed-in.
- Steps: navigate to `/call-history`.
- **Mock API**: `POST /call-log/list` → `500 { "detail": "Database connection error" }`
- Expected UI: error toast title "Database connection error" (variant `error`); table shows loading→empty; no row click possible.

**FS-2: Unauthorized list (401)**
- Preconditions: stale token.
- **Mock API**: `POST /call-log/list` → `401 {"detail": "Could not validate credentials"}`
- Expected UI: error toast "Could not validate credentials"; middleware-level redirect MAY fire on next nav.

**FS-3: Empty list — no filters**
- **Mock API**: `POST /call-log/list` → `{"items": [], "total": 0, "page": 1, "page_size": 10}`
- Expected UI: "No call logs found" headline + "Call logs will appear here once your agents start handling calls." No "Clear all filters" button.

**FS-4: Empty list — under active filters**
- Preconditions: at least one filter applied (chip visible).
- **Mock API**: same as FS-3.
- Expected UI: "No call logs found" + "No calls match your current filters. Try adjusting or clearing them." + "Clear all filters" button (Clear all dispatches reset).

**FS-5: Audio URL fetch fails (404)**
- Preconditions: detail page open; `recording_upload_id` present.
- **Mock API**: `GET /call-log/<id>/audio-url` → `404 {"detail": "Call not found"}`
- Expected UI: error toast "Call not found"; player area shows "Failed to load audio" (no `<audio>` element).

**FS-6: No `recording_upload_id`**
- Preconditions: detail page open.
- **Mock API**: `GET /call-log/<id>` returns a call without `recording_upload_id`.
- Expected UI: text "No audio recording available"; NO `GET /audio-url` call fires.

**FS-7: Empty transcript**
- Preconditions: `GET /call-log/<id>` returns `transcript: []` or absent.
- Expected UI: under Transcription h3, text "No transcription available"; transcript search input NOT rendered.

**FS-8: Transcript search returns no matches**
- Preconditions: transcript loaded.
- Steps: type `xyzzy`.
- Expected UI: text "No matching messages" (centered, muted). No `<mark>` elements.

**FS-9: Detail fetch fails**
- **Mock API**: `GET /call-log/<id>` → `404 {"detail": "Call not found"}`
- Expected UI: error toast "Call not found"; summary card not rendered (callLog stays null).

**FS-10: Facets fetch fails**
- **Mock API**: `POST /call-log/facets` → `400 {"detail": "Unknown facet field: foo"}`
- Expected UI: drawer facet sections render with spinner/empty state; no toast spam (current code silently catches). Marked `⚠ unverified` — confirm handler.

---

## Expected Toast Messages

Sourced from `src/utils/toast.tsx` + `src/utils/helpers.ts` (`handleApiError` lifts `error.response.data.detail`).

| Trigger                                       | Toast title (= `detail`)                    | Toast description | Variant |
| --------------------------------------------- | ------------------------------------------- | ----------------- | ------- |
| `POST /call-log/list` 500                     | `Database connection error` (from response) | (none)            | error   |
| `POST /call-log/list` 401                     | `Could not validate credentials`            | (none)            | error   |
| `POST /call-log/list` network failure         | `Something went wrong. Please try again.`   | (none)            | error   |
| `GET /call-log/<id>` 404                      | `Call not found`                            | (none)            | error   |
| `GET /call-log/<id>/audio-url` 404            | `Call not found`                            | (none)            | error   |
| Clipboard write fails (Copy link)             | (no toast — fails silently per code)        | —                 | —       |

> Toasts use the Sonner `showToast.error(title)` shape — a single line, no description. Tests should assert `page.locator('[data-sonner-toast]').first()` contains the exact `detail` string.

---

## UI Elements

| Element                       | Type           | Content / Label                                                  | Behavior                                                       |
| ----------------------------- | -------------- | ---------------------------------------------------------------- | -------------------------------------------------------------- |
| Page heading                  | h1             | "Call History"                                                   | Static                                                         |
| Total badge                   | Badge          | Phone icon + count                                               | Reflects `callLogsAtom.total`                                  |
| Token search bar              | Input          | "Filter by field… (e.g. status:completed)"                       | Token-based filter values for `POST /call-log/list`            |
| Columns button                | Button         | "Columns" + Columns3 icon + hidden-count badge                   | Opens column-visibility popover                                |
| Columns popover               | Popover        | Groups: Call History + Call Metrics; per-column toggles          | Reset + Apply                                                  |
| Filters button                | Button         | "Filters" + SlidersHorizontal icon + drawer-filter count         | Opens drawer                                                   |
| Table column: Agent           | Cell (sticky)  | AgentTypeBadge                                                   | Sticky-left, always visible                                    |
| Table column: Status          | Badge          | colored per status (completed / failed / …)                      | —                                                              |
| Table column: Duration        | Cell           | recording length if available, else computed                     | —                                                              |
| Table columns: From / To      | Cell           | flag + E.164 phone                                               | —                                                              |
| Table columns: Started / Ended| Cell           | timezone-formatted timestamps                                    | —                                                              |
| Metric columns                | Cell           | Avg Latency, LLM Tokens, TTS Chars, Turns                        | Toggleable group                                               |
| Pagination                    | Pagination     | 10 / 25 / 50 / 100                                               | Page resets on filter/sort/size change                         |
| Filter drawer — Timeline      | DateRangePicker | full-width                                                       | Triggers state on change                                       |
| Filter drawer — Facet section | Toggle list    | label + spinner + values                                         | Values come from `/call-log/facets`                            |
| Filter drawer — Turns         | Number inputs  | From / To, min 0                                                 | Helper text about excluded rows                                |
| Filter drawer — Latency       | Slider         | 0–10 s, step 0.1 s; labels at bounds                             | —                                                              |
| Filter drawer — Reset         | Button         | "Reset"                                                          | Disabled when no filters are active                            |
| Filter drawer — Apply         | Button         | "Apply"                                                          | Commits the draft to applied state                             |
| Detail header — breadcrumb    | Text           | "Call History / Agent Name"                                      | Linkable up to list                                            |
| Detail header — call id pill  | Pill           | truncated id; tooltip shows full id                              | —                                                              |
| Detail header — Copy link     | Button         | "Copy link" / transient "Copied" + Check icon                    | Renders "Copied" for ~1.5 s                                    |
| Summary card chips            | Chips          | status / duration / phones / channel / times                     | Static per call                                                |
| Audio player                  | `<audio>`      | HTML5 controls                                                   | Loading / error / missing states                               |
| Transcript search             | TextInput      | "Search transcription…"                                          | Highlights matches with yellow `<mark>`                        |
| Chat message bubble           | Card           | role label + text + timestamp                                    | User left muted bg / Assistant right primary bg                |
| Metrics chart toggle          | Toggle         | Chart / Table                                                    | Switches view per chart                                        |

---

## Navigation

| Trigger                          | Destination                                  | Condition                              |
| -------------------------------- | -------------------------------------------- | -------------------------------------- |
| Click a row                      | `/call-history/[callId]/transcription`       | Always                                 |
| Visit `/call-history/[callId]`   | `/call-history/[callId]/transcription`       | Redirect                               |
| Click a tab in the sidebar       | `/call-history/[callId]/<tab>`               | Always                                 |
| Click "Back to Call History"     | `/call-history`                              | Always                                 |
| Click "Copy link"                | Writes the URL to clipboard; chip flips      | Always                                 |
| Open Columns popover             | Toggle column visibility (state only)        | Always                                 |
| Open Filters drawer              | Draft filter state                           | Always                                 |
| Click "Apply" in drawer          | Commit filters → refetch list                | Always                                 |
| Click "Reset" in drawer          | Clears draft filters                         | At least one filter is active          |
| No auth cookie                   | `/auth/login?redirect=%2Fcall-history`       | `src/middleware.ts` redirect           |

---

## API Contracts

| Endpoint                                          | Method | Request                                                                                | Success Response                                | Error Response       |
| ------------------------------------------------- | ------ | -------------------------------------------------------------------------------------- | ----------------------------------------------- | -------------------- |
| `/call-log/list`                                  | POST   | `{ page_no, page_size, filters, start_date_time, end_date_time, sort_by, sort_order }` | `{ items: CallLog[], total }`                   | `{ detail: "..." }`  |
| `/call-log/facets`                                | POST   | `{ start_date_time, end_date_time, filters }`                                          | `{ facets: { [field]: { value, count }[] } }`   | `{ detail: "..." }`  |
| `/call-log/filter-values?column_name=<field>`     | GET    | —                                                                                      | `{ values: string[] }`                          | `{ detail: "..." }`  |
| `/call-log/{callId}`                              | GET    | —                                                                                      | `{ call: CallLog }`                             | `{ detail: "..." }`  |
| `/call-log/{callId}/audio-url`                    | GET    | —                                                                                      | `{ audio_url: string }`                         | `{ detail: "..." }`  |

State is held in Jotai atoms `callLogsAtom`, `callFacetsAtom` and the write
atoms `fetchCallLogs`, `fetchCallFacets`. The detail tabs read from
`CallDetailContext` (`useCallDetail`).

> Source: real values copied from `postman_collection/Tone-API.postman_collection.json`
> folder `Call Logs`. The folder may be marked disabled in some environments but
> the request/response examples below remain canonical and should be used as
> Playwright mock fixtures.

### Example — `POST /call-log/list`

Request body:
```json
{
  "page_no": 1,
  "page_size": 10,
  "start_date_time": "2026-05-01T00:00:00+00:00",
  "end_date_time": "2026-05-31T23:59:59+00:00",
  "filters": [
    {"field": "status", "operator": "eq", "value": "completed"}
  ],
  "sort_by": "started_at",
  "sort_order": "desc"
}
```
Success body (200):
```json
{
  "items": [
    {
      "id": "call-uuid",
      "agent_id": "agent-uuid",
      "from_number": "+14155550100",
      "to_number": "+14155550199",
      "status": "completed",
      "duration_seconds": 132,
      "started_at": "2026-05-15T10:00:00+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```
Validation error body (422):
```json
{
  "detail": [
    {"loc": ["body", "field"], "msg": "field required", "type": "value_error.missing"}
  ]
}
```
Other error bodies: `400 {"detail": "Invalid start_date_time format"}`, `401 {"detail": "Could not validate credentials"}`.

### Example — `POST /call-log/facets`

Request body:
```json
{
  "start_date_time": "2026-05-01T00:00:00+00:00",
  "end_date_time": "2026-05-31T23:59:59+00:00",
  "filters": []
}
```
Success body (200):
```json
{ "status": {"completed": 12, "failed": 1, "in_progress": 0} }
```
Error body (400): `{"detail": "Unknown facet field: foo"}`.

### Example — `GET /call-log/filter-values?column_name=status`

Success body (200):
```json
{ "values": ["completed", "failed", "in_progress"] }
```
Error body (400): `{"detail": "column_name is required"}`.

### Example — `GET /call-log/{call_id}`

Success body (200):
```json
{
  "id": "call-uuid",
  "agent_id": "agent-uuid",
  "from_number": "+14155550100",
  "to_number": "+14155550199",
  "status": "completed",
  "duration_seconds": 132,
  "transcript": [
    {"role": "assistant", "text": "Hi, how can I help?"},
    {"role": "user", "text": "I need to reschedule."}
  ]
}
```
Error body (404): `{"detail": "Call not found"}`.

### Example — `GET /call-log/{call_id}/audio-url`

Success body (200):
```json
{ "audio_url": "https://r2.example.com/calls/call-uuid.mp3?signature=..." }
```
Error body (404): `{"detail": "Call not found"}`.

> ⚠ unverified: the frontend reads transcript message timestamps but the
> Postman example omits the `timestamp` field on transcript entries. Use the
> richer shape from PS-3 above when generating tests.

---

## Edge Cases

- [ ] Unauthenticated access → middleware redirect
- [ ] List is empty (no calls at all) → "No call logs found" + "Call logs will appear here once your agents start handling calls."
- [ ] List is empty under active filters → "No calls match your current filters. Try adjusting or clearing them." + "Clear all filters"
- [ ] Audio URL fetch fails → "Failed to load audio"
- [ ] No `recording_upload_id` on the call → "No audio recording available"
- [ ] No transcript → "No transcription available"
- [ ] Transcript search returns no matches → "No matching messages"
- [ ] Filters that require metrics (turns range, latency range) automatically exclude calls without metrics (documented in drawer helper text)
- [ ] Browser time zone captured once on filter-state init via `getBrowserTimeZone`
- [ ] Column visibility resets when navigating away from `/call-history`
- [ ] Sort or page-size change resets the page index to 1
- [ ] Copy link state: "Copied" indicator clears after ~1.5 s
- [ ] Filter drawer closed without Apply: draft is discarded, applied filters remain
- [ ] Timezone-aware filter sends: every `POST /call-log/list` and `POST /call-log/facets` payload includes `start_date_time` / `end_date_time` ISO-8601 strings with the browser's offset captured once via `getBrowserTimeZone()` at module init (`BROWSER_TZ` constant in `CallHistory.tsx`)
- [ ] Column visibility persistence across navigation: column visibility is component-local state — leaving and returning to `/call-history` resets to defaults (no localStorage hydration today)
- [ ] Copy-link clipboard permission denied: `navigator.clipboard.writeText` rejection is caught silently in `CopyLinkButton` — no toast, button stays "Copy link"
- [ ] Insecure context (HTTP, not HTTPS): `navigator.clipboard` may be `undefined`; Copy link no-ops
- [ ] Avatar / row icon image 404: ⚠ unverified — list rows currently do not render call-level avatars; row-level fallback handled by `AgentTypeBadge` text only
- [ ] Sort while a previous list-fetch is in flight: latest request wins (no abort controller) — UI may briefly flash the older page
- [ ] Switching tabs within a detail page does NOT refetch `GET /call-log/<id>` — `CallDetailContext` memoizes the single fetch
- [ ] Detail page hard-loaded for a stale id with an active filter set on `/call-history`: back-nav returns to the list with filters preserved (filter state is module-level)

---

## Business Rules

- The list endpoint is server-driven for filters, sort, pagination, and facets — no client-side filtering on already-fetched rows.
- Date range is always sent with an explicit time zone; backend interprets `start_date_time` / `end_date_time` accordingly.
- "Duration" prefers recording length over `(ended_at - started_at)` when both are available.
- Status colors follow a fixed mapping (e.g. completed = green, failed = red); badges include the status text.
- The detail tabs share a single `CallDetailContext` instance so siblings don't refetch the call independently.

---

## Accessibility Requirements

- [ ] Token search input has an accessible label
- [ ] Columns popover groups have group-toggle controls labeled by name
- [ ] Filter drawer traps focus and restores it on close
- [ ] Chat message bubbles use proper roles + names for screen readers (User says "…", Assistant says "…")
- [ ] Audio player uses native `<audio controls>` (built-in keyboard + AT support)
- [ ] Transcript search highlights stay readable in dark mode (yellow `<mark>` with sufficient contrast)
- [ ] Tab pills (desktop sidebar + mobile bar) expose `aria-current="page"` for the active tab
- [ ] Copy-link button announces the success state via `aria-live` or by updating its accessible name to "Copied"

---

## Appended Scenarios (gap-fill, ID prefix `CH-`)

These rows extend the PS/FS coverage with auth/error-state/network/a11y/list-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `call-history.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-001 | Visit `/call-history` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fcall-history` | `unauthenticated visit redirects to login` |
| CH-002 | Visit `/call-history` with an expired token cookie | Middleware 307 → `/auth/login?redirect=%2Fcall-history`; expired cookie cleared on the login response | `expired token redirects to login and clears cookie` |
| CH-003 | Visit `/call-history/<callId>` deep link without auth | Middleware 307 → `/auth/login?redirect=%2Fcall-history%2F<callId>` | `unauthenticated detail deep link redirects to login` |
| CH-004 | Logged-in non-member opens `/call-history` (org switched away) | Access-denied state OR redirect to `/home`; no `POST /call-log/list` fires | `non-member is denied access to call history list` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-005 | `POST /call-log/list` returns 400 (malformed token search payload) | Empty table state; toast surfaces backend `detail`; no client crash | `list 400 surfaces detail toast and renders empty state` |
| CH-006 | Token expires between list load and a row click → 401 on `GET /call-log/<id>` | Toast `Could not validate credentials`; summary card not rendered | `detail 401 surfaces error toast without redirect` |
| CH-007 | Member role with no call access on a deep link → 403 | Toast `Forbidden`; empty detail; sidebar tabs remain visible | `detail 403 surfaces forbidden toast` |
| CH-008 | Detail load returns 404 for an unknown call id | Toast `Call not found`; summary card hidden; tabs render empty states | `detail 404 surfaces not-found toast` |
| CH-009 | `POST /call-log/facets` returns 409 unsupported field | Drawer facet sections render empty; no toast spam; list still loads | `facets 409 keeps drawer usable without spam` |
| CH-010 | `POST /call-log/list` returns 500 mid-search | Skeleton clears; empty-state body renders; toast surfaces server `detail` | `list 500 falls back to empty state with toast` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-011 | Offline / network failure during `POST /call-log/list` | Skeleton clears; toast `Something went wrong. Please try again.`; subsequent retry refills the table | `list network failure surfaces toast then recovers on retry` |
| CH-012 | Slow `POST /call-log/list` (>3s) | Skeleton rows visible the whole time; toolbar (search/filters/columns) remains enabled | `slow list keeps skeleton visible without blocking the toolbar` |
| CH-013 | Slow `GET /call-log/<id>/audio-url` (>3s) | "Loading audio…" spinner visible the whole time; transcript still renders | `slow audio URL fetch keeps loader without blocking transcript` |
| CH-014 | Concurrent filter changes — second `POST /call-log/list` while first is in-flight | Latest request wins; UI does not flash an older page; no toast | `concurrent list fetches resolve to the latest response` |

### Input edge cases (token search + transcript search)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-015 | Type only whitespace into the token search bar | No `filters` change; table reverts to default | `whitespace-only token search is treated as empty` |
| CH-016 | Token search with leading/trailing spaces (` status:completed `) | Trimmed before send; payload contains `status:completed` | `token search trims surrounding whitespace` |
| CH-017 | Token search with special chars (`<script>`, emoji, unicode) | Sent verbatim; no XSS execution; UI renders without breaking | `token search accepts unicode and html-ish input without xss` |
| CH-018 | Token search > 500 characters | Either accepted in one request or truncated; no crash | `very long token search does not crash the page` |
| CH-019 | Transcript search uses a regex-special string (`.*`, `(foo)`) | Regex escape via `escapeRegex`; matches treated as literal substring; highlights still render | `transcript search escapes regex special characters` |
| CH-020 | Transcript search with whitespace-only value | No `<mark>` rendered; full transcript still visible | `whitespace-only transcript search restores full transcript` |
| CH-021 | Future date in the Timeline picker | Picker disables future days OR API returns empty; UI does not crash | `future date filter handled gracefully` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-022 | Empty list with no filters | "No call logs found" + "Call logs will appear here once your agents start handling calls." | `empty list renders the no-calls empty state` |
| CH-023 | Search with no matches under active filters | "No calls match your current filters. Try adjusting or clearing them." + "Clear all filters" button | `filtered search with no matches renders the no-results state` |
| CH-024 | Pagination — first page | Prev disabled, Next enabled when more pages exist | `pagination disables prev on the first page` |
| CH-025 | Pagination — last page | Next disabled, Prev enabled | `pagination disables next on the last page` |
| CH-026 | Sort by Started At (asc → desc) | Two consecutive header clicks fire two list calls with `sort_by: 'started_at'` asc then desc | `sort by Started At cycles asc and desc` |
| CH-027 | Sort by Duration | `POST /call-log/list` fires with `sort_by: 'duration_seconds'` | `sort by Duration orders rows by duration` |
| CH-028 | Date range filter — default range applied on first load | Payload contains a sensible `start_date_time`/`end_date_time` pair with the browser tz | `default date range is applied on first load` |
| CH-029 | Date range filter — custom range picked via drawer | After Apply, `POST /call-log/list` fires with the chosen ISO-8601 range | `custom date range refetches the list` |
| CH-030 | Drawer filter chip removable | Clicking the chip's X removes that single filter; list refetches | `removing a single filter chip refetches without it` |
| CH-031 | "Clear all filters" empty-state CTA | Resets every drawer/toolbar filter; list refetches; badge count returns to 0 | `clear all filters resets drawer and toolbar state` |
| CH-032 | Column visibility popover — toggle one column off | Column hidden; hidden-count badge increments by 1; new columns persist while on the page | `toggling a column updates the hidden count badge` |
| CH-033 | Page-size 10/25/50/100 each reset page to 1 | Each change refires `POST /call-log/list` with the new size and `page_no: 1` | `changing page size resets to page 1` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-034 | Tab order through the toolbar | Token search → Columns → Filters → first sortable header — reachable in order | `tab order through toolbar reaches every control` |
| CH-035 | Filter drawer traps focus and restores it on close | Focus moves inside the drawer; Tab cycles within; Esc closes and restores focus to the Filters button | `filter drawer traps focus and restores on close` |
| CH-036 | Press Enter on a sortable column header | Re-fires `POST /call-log/list` with updated sort (same as click) | `Enter on sortable header triggers sort` |
| CH-037 | Toast error has `role="alert"` / aria-live | Screen readers announce the toast title without manual focus | `error toast is announced via aria-live` |
| CH-038 | Detail page sidebar tab pills expose `aria-current="page"` | Active tab has `aria-current="page"`; others do not | `active detail tab exposes aria-current` |
| CH-039 | Audio player uses native `<audio controls>` | Native keyboard shortcuts (space, arrows) work; no custom widget | `audio player exposes native keyboard controls` |
| CH-040 | Copy link button announces success | Button accessible name flips to "Copied" for ~1.5s; aria-live region OR text update | `copy link button announces success state` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-041 | Click "Back to Call History" from detail | URL returns to `/call-history`; list state (filters, page) preserved | `back to call history preserves list state` |
| CH-042 | Breadcrumb "Call History" link from detail | Navigates to `/call-history` | `breadcrumb link returns to list` |
| CH-043 | Browser back button after row click | Returns to `/call-history` with the same filters intact | `browser back from detail returns to filtered list` |
| CH-044 | Reload detail page directly via deep link | Detail tabs render after fetch; no fallback to the list | `reload on detail deep link renders without redirect` |
| CH-045 | Copy link from detail → open in a new tab | New tab loads the same call detail (auth permitting) | `copy link target opens the same call in a new tab` |

### Full lifecycle (`CH-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CH-FULL | Authenticate via `loginViaUI` → visit `/call-history` → assert headings + total badge → exercise token search (`status:completed`) and clear → open Filters drawer → pick a 7-day range + facet (Direction=outbound) → Apply → assert toolbar badge `1` and list refetch → reopen drawer → Reset → assert badge gone → toggle a column off → change page size to 25 → click first row → land on `/call-history/<id>/transcription` → assert breadcrumb + summary card + audio loader → switch to Metrics tab → switch to Configurations tab → click "Back to Call History" → assert URL is `/call-history` and filters cleared → click "Copy link" on a freshly opened detail and assert "Copied" state | Every documented toolbar/drawer/tab affordance fires the expected request; no leaked listeners; for any seeded `__e2e__` call data, cleanup runs via `try/finally` in the same test body | `walks the entire call history list and detail end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| CH-001..004 | (new) | Auth-gating, expired-token, deep-link, non-member |
| CH-005..010 | FS-1..FS-10 | Standardises 400/401/403/404/409/500 paths |
| CH-011..014 | (new) | Network resilience for list, audio URL, concurrent fetches |
| CH-015..021 | (new) | Input edge cases for token + transcript search and date pickers |
| CH-022..033 | PS-2, FS-3, FS-4 | Pagination/sort/empty-state/column visibility promoted to scenarios |
| CH-034..040 | Accessibility section | Promotes a11y bullets to runnable scenarios |
| CH-041..045 | Navigation table | Adds back/forward/reload/new-tab checks |
| CH-FULL | (new) | Single-test sweep across list + drawer + tabs + copy link |
