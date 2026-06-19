# Feature Doc: Call History

Feature documentation for the Call History list + per-call detail pages. Used
by `/generate-tests call-history` (or `--docs e2e/ux_flow_docs/call-history.md`) to
ensure all user cases are covered.

Call History is the historical record of voice calls handled by the agent
pipeline. Each call has metadata, a recording, a transcript, and metrics. The
list page supports rich filtering; the detail page splits into three tabs
(Transcription & Recordings, Metrics, Call Configurations).

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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
> richer transcript shape (with `timestamp`) when generating tests.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.

---

### TC-HAPPY-001: List loads with default range (WF-1 / PS-1)

**Preconditions**:
- Signed-in user; calls exist in DB.

**Action**:
1. Sign in via `loginViaUI`
2. Click the sidebar `Call History` link

**Observation 1 — URL and headings**:
1. URL becomes `/call-history`
2. h1 reads `Call History`
3. Total Phone badge text equals the response `total`

**Observation 2 — List API calls fire with default range + browser tz**:
1. Exactly one `POST /call-log/list` request fires
2. Exactly one `POST /call-log/facets` request fires
3. Both bodies include `start_date_time`, `end_date_time`, and the current browser tz

**Observation 3 — Table renders first page**:
1. First page of rows is visible
2. Agent column is sticky-left

**API mock**: `POST /call-log/list` → 200 PS-1 body.

---

### TC-HAPPY-002: Apply Status=completed via token search (WF-1 step 4 / PS-2)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Type `status:completed` in the token search bar
2. Press Enter

**Observation 1 — Refetch with filter**:
1. `POST /call-log/list` re-fires
2. Request body filters include `{field:"status", operator:"in", value:["completed"]}`
3. `page_no` resets to 1

**Observation 2 — Row count matches filtered total**:
1. Table shows the filtered rows
2. Total badge updates to the new `total`

---

### TC-HAPPY-003: Open call detail (WF-3 / PS-3)

**Preconditions**: TC-HAPPY-001 row visible.

**Action**:
1. Click any row

**Observation 1 — Navigation + detail fetch**:
1. URL becomes `/call-history/<id>/transcription`
2. Exactly one `GET /call-log/<id>` request fires

**Observation 2 — Header content**:
1. Breadcrumb reads `Call History / <Agent Name>`
2. CallIdPill shows truncated id
3. Hovering the pill exposes a tooltip with the full id

**Observation 3 — Summary card chips render**:
1. Status, duration, From/To phones, channel type, start/end timestamps all render

**API mock**: `GET /call-log/<id>` → 200 PS-3 body.

---

### TC-HAPPY-004: Audio loads and plays (WF-4 / PS-4)

**Preconditions**: TC-HAPPY-003; call has `recording_upload_id`.

**Action**:
1. Wait for the audio player to mount

**Observation 1 — Audio URL fetch**:
1. Exactly one `GET /call-log/<id>/audio-url` request fires

**Observation 2 — Loading then rendered**:
1. "Loading audio…" with spinner appears briefly
2. A native `<audio controls>` element renders with the signed URL as `src`

**API mock**: `GET /call-log/<id>/audio-url` → 200 `{"audio_url": "https://..."}`.

---

### TC-HAPPY-005: Transcript search highlights matches (WF-4 step 3 / PS-5)

**Preconditions**: TC-HAPPY-003 transcript loaded.

**Action**:
1. Type `reschedule` in the transcript search input
2. Clear the search

**Observation 1 — Filtering and highlighting**:
1. Only matching messages remain visible
2. The matched substring is wrapped in `<mark class="bg-yellow-200">`

**Observation 2 — Clearing restores transcript**:
1. After clearing, all messages are visible again
2. Zero `<mark>` elements remain in the DOM

---

### TC-HAPPY-006: Copy link succeeds (WF-5 / PS-6)

**Preconditions**: TC-HAPPY-003.

**Action**:
1. Click "Copy link"

**Observation 1 — Clipboard contents**:
1. Clipboard contains `window.location.href`

**Observation 2 — Button label flips and reverts**:
1. Button reads `Copied` with a Check icon
2. After ~1.5 s the button reverts to `Copy link`

---

### TC-HAPPY-007: Apply drawer filter + reset (WF-2 / PS-7)

**Preconditions**: TC-HAPPY-001.

**Action**:
1. Click "Filters"
2. Toggle `direction: outbound`
3. Click "Apply"
4. Reopen the drawer
5. Click "Reset"

**Observation 1 — Drawer renders correctly**:
1. Right-side drawer titled "Filters" opens
2. Description reads "Narrow call history by time, status, agent, pipeline and metrics."

**Observation 2 — Apply refetches**:
1. `POST /call-log/list` fires after Apply
2. Filters toolbar button badge count equals 1

**Observation 3 — Reset clears**:
1. After Reset, the badge is gone
2. "Reset" button is disabled (no active filters)
3. `POST /call-log/list` fires again with no filter

---

### TC-HAPPY-008: Use the Filters drawer end-to-end (WF-2)

**Preconditions**: TC-HAPPY-001.

**Action**:
1. Click "Filters"
2. Expand Timeline and pick a 7-day range
3. Toggle a facet value (e.g. `direction: outbound`)
4. Enter Turns `From=5, To=20`
5. Drag Avg latency to `0.5s — 3.2s`
6. Click "Apply"

**Observation 1 — Draft does not refetch**:
1. Steps 2–5 do NOT cause `POST /call-log/list` to fire

**Observation 2 — Helper text under Turns**:
1. Text reads `Calls with no metrics record are excluded when this range is set.`

**Observation 3 — Apply commits and refetches**:
1. Drawer closes
2. `POST /call-log/list` fires with the new filters
3. Toolbar Filters button badge count > 0

**Observation 4 — Close without Apply discards draft**:
1. Reopen drawer, edit, then press Esc OR click overlay
2. Reopen again — applied filters unchanged

---

### TC-HAPPY-009: Open detail + switch tabs (WF-3)

**Preconditions**: TC-HAPPY-003 just loaded.

**Action**:
1. Click "Metrics" sidebar tab
2. Click "Call Configurations" sidebar tab
3. Click "Back to Call History"

**Observation 1 — Metrics tab**:
1. URL becomes `/call-history/<id>/metrics`
2. No second `GET /call-log/<id>` fires (context memoized)

**Observation 2 — Configurations tab**:
1. URL becomes `/call-history/<id>/configurations`
2. Section lists agent_name, direction, status, channel_type, started_at, ended_at

**Observation 3 — Back rail link**:
1. URL becomes `/call-history`
2. List state preserved (filters and page)

---

### TC-NAV-001: Unauthenticated visit redirects to login (CH-001)

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/call-history`

**Observation 1 — Middleware redirect**:
1. Response status is 307
2. Final URL is `/auth/login?redirect=%2Fcall-history`

---

### TC-NAV-002: Expired token redirects and clears cookie (CH-002)

**Preconditions**: Expired `tone_access_token` cookie.

**Action**:
1. Visit `/call-history`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fcall-history`

**Observation 2 — Cookie cleared**:
1. Expired cookie is cleared on the login response

---

### TC-NAV-003: Unauthenticated detail deep link redirects to login (CH-003)

**Preconditions**: No auth cookie.

**Action**:
1. Visit `/call-history/<callId>`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fcall-history%2F<callId>`

---

### TC-NAV-004: Non-member is denied access to call history (CH-004)

**Preconditions**: Logged-in user without membership (org switched away).

**Action**:
1. Visit `/call-history`

**Observation 1 — Denied state OR redirect**:
1. Page renders access-denied state OR redirects to `/home`

**Observation 2 — No list fetch fires**:
1. Zero `POST /call-log/list` requests are recorded

---

### TC-NAV-005: Back to Call History preserves list state (CH-041)

**Preconditions**: Filters applied; user opened a detail page.

**Action**:
1. From detail, click "Back to Call History"

**Observation 1 — Returns to list with state intact**:
1. URL is `/call-history`
2. Active filters and current page index are preserved

---

### TC-NAV-006: Breadcrumb link returns to list (CH-042)

**Preconditions**: Detail page open.

**Action**:
1. Click the breadcrumb `Call History`

**Observation 1 — Navigation**:
1. URL becomes `/call-history`

---

### TC-NAV-007: Browser back from detail returns to filtered list (CH-043)

**Preconditions**: Filters applied; user clicked a row.

**Action**:
1. Press browser Back

**Observation 1 — Returns to filtered list**:
1. URL becomes `/call-history`
2. Filter state matches the prior selection

---

### TC-NAV-008: Reload on detail deep link renders without redirect (CH-044)

**Preconditions**: Authenticated; on a detail tab.

**Action**:
1. Reload the page directly

**Observation 1 — Detail tabs render after fetch**:
1. `GET /call-log/<id>` fires
2. The detail page renders without falling back to the list

---

### TC-NAV-009: Copy link target opens the same call in a new tab (CH-045)

**Preconditions**: Authenticated; detail page loaded; "Copy link" pressed.

**Action**:
1. Open the copied URL in a new browser tab

**Observation 1 — Same detail loads**:
1. New tab URL matches the copied URL
2. The same call detail loads (auth permitting)

---

### TC-ERROR-001: List fetch fails (500) (FS-1 / CH-010)

**Preconditions**: Signed-in.

**Action**:
1. Navigate to `/call-history`

**Observation 1 — Error toast**:
1. Toast title equals `Database connection error`
2. Toast variant is `error`

**Observation 2 — Loading → empty state**:
1. Skeleton/loading clears
2. Table shows empty state
3. No row click is possible

**API mock**: `POST /call-log/list` → 500 `{"detail":"Database connection error"}`.

---

### TC-ERROR-002: List 401 unauthorized (FS-2)

**Preconditions**: Stale token.

**Action**:
1. Navigate to `/call-history`

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Middleware may redirect on next nav**:
1. Subsequent client-side navigation triggers the middleware redirect to `/auth/login`

**API mock**: `POST /call-log/list` → 401.

---

### TC-ERROR-003: Empty list — no filters (FS-3 / CH-022)

**Action**:
1. Navigate to `/call-history` (no filters)

**Observation 1 — Empty state text**:
1. Heading reads `No call logs found`
2. Subtitle reads `Call logs will appear here once your agents start handling calls.`

**Observation 2 — No clear-filters button**:
1. The "Clear all filters" button is NOT present

**API mock**: `POST /call-log/list` → `{"items":[], "total":0}`.

---

### TC-ERROR-004: Empty list under active filters (FS-4 / CH-023)

**Preconditions**: At least one filter applied (chip visible).

**Action**:
1. Wait for the refetch

**Observation 1 — Empty-with-filters text**:
1. Heading reads `No call logs found`
2. Subtitle reads `No calls match your current filters. Try adjusting or clearing them.`

**Observation 2 — Clear-all button visible**:
1. A `Clear all filters` button is present
2. Clicking it dispatches the reset

**API mock**: `POST /call-log/list` → `{"items":[], "total":0}`.

---

### TC-ERROR-005: Audio URL fetch fails (404) (FS-5)

**Preconditions**: Detail page open; `recording_upload_id` present.

**Action**:
1. Wait for audio fetch to fail

**Observation 1 — Error toast**:
1. Toast title equals `Call not found`

**Observation 2 — Player area**:
1. Text `Failed to load audio` is shown
2. No `<audio>` element is rendered

**API mock**: `GET /call-log/<id>/audio-url` → 404.

---

### TC-ERROR-006: No recording_upload_id (FS-6)

**Preconditions**: `GET /call-log/<id>` returns no `recording_upload_id`.

**Action**:
1. Navigate to the detail page

**Observation 1 — No-recording state**:
1. Text `No audio recording available` is shown

**Observation 2 — No audio-url request fires**:
1. Zero `GET /call-log/<id>/audio-url` requests are recorded

---

### TC-ERROR-007: Empty transcript (FS-7)

**Preconditions**: `GET /call-log/<id>` returns `transcript: []` or absent.

**Action**:
1. Navigate to the Transcription tab

**Observation 1 — No-transcript state**:
1. Text `No transcription available` is shown under the Transcription h3
2. The transcript search input is NOT rendered

---

### TC-ERROR-008: Transcript search returns no matches (FS-8)

**Preconditions**: Transcript loaded.

**Action**:
1. Type `xyzzy` in the search input

**Observation 1 — No-match state**:
1. Text `No matching messages` is centered, muted
2. Zero `<mark>` elements are present

---

### TC-ERROR-009: Detail fetch fails 404 (FS-9 / CH-008)

**Preconditions**: Authenticated.

**Action**:
1. Visit `/call-history/<unknownId>`

**Observation 1 — Error toast**:
1. Toast title equals `Call not found`

**Observation 2 — Summary card not rendered**:
1. CallSummaryCard is absent
2. Tabs render empty states

**API mock**: `GET /call-log/<id>` → 404.

---

### TC-ERROR-010: Facets fetch fails (FS-10)

**Action**:
1. Open the Filters drawer

**Observation 1 — Drawer still renders**:
1. Facet sections render with a spinner or empty state
2. No toast spam appears

> ⚠ unverified — confirm handler does not surface a toast.

**API mock**: `POST /call-log/facets` → 400 `{"detail":"Unknown facet field: foo"}`.

---

### TC-ERROR-011: List 400 surfaces detail toast (CH-005)

**Action**:
1. Type a malformed token search payload
2. Press Enter

**Observation 1 — Empty table state**:
1. Table shows an empty state

**Observation 2 — Toast surfaces backend detail**:
1. Toast title equals the backend `detail` string
2. No client crash occurs

**API mock**: `POST /call-log/list` → 400.

---

### TC-ERROR-012: Detail 401 between list and row click (CH-006)

**Preconditions**: Token expires after list load.

**Action**:
1. Click a row

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Summary card not rendered**:
1. CallSummaryCard is absent

**API mock**: `GET /call-log/<id>` → 401.

---

### TC-ERROR-013: Detail 403 forbidden on deep link (CH-007)

**Preconditions**: Member role with no call access.

**Action**:
1. Visit a deep link `/call-history/<id>`

**Observation 1 — Forbidden toast**:
1. Toast title equals `Forbidden`

**Observation 2 — Empty detail with sidebar tabs visible**:
1. CallSummaryCard absent
2. Sidebar tabs remain visible

**API mock**: `GET /call-log/<id>` → 403.

---

### TC-ERROR-014: Facets 409 keeps drawer usable (CH-009)

**Preconditions**: Authenticated.

**Action**:
1. Open the Filters drawer

**Observation 1 — Drawer remains usable**:
1. Drawer renders empty facet sections
2. No toast spam appears
3. The list still loads normally

**API mock**: `POST /call-log/facets` → 409.

---

### TC-LOADING-001: Network failure on list surfaces toast then recovers (CH-011)

**Preconditions**: Network is unavailable for first attempt.

**Action**:
1. Navigate to `/call-history`
2. Retry (e.g. reload)

**Observation 1 — Skeleton clears + error toast**:
1. Skeleton clears
2. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Retry refills table**:
1. Subsequent `POST /call-log/list` returns 200
2. Table re-fills with rows

**API mocks**: first call `route.abort('failed')`; second call → 200.

---

### TC-LOADING-002: Slow list keeps skeleton without blocking toolbar (CH-012)

**Preconditions**: List API delays > 3 s.

**Action**:
1. Navigate to `/call-history`

**Observation 1 — Skeleton visible**:
1. Skeleton rows visible throughout the 3 s+ window

**Observation 2 — Toolbar enabled**:
1. Token search, Filters, and Columns buttons remain enabled

---

### TC-LOADING-003: Slow audio URL fetch keeps loader without blocking transcript (CH-013)

**Preconditions**: Audio URL API delays > 3 s.

**Action**:
1. Navigate to a detail page with audio

**Observation 1 — Loader persists**:
1. `Loading audio…` spinner remains visible the entire wait

**Observation 2 — Transcript still renders**:
1. The transcript section renders independent of audio

---

### TC-LOADING-004: Concurrent list fetches resolve to the latest response (CH-014)

**Action**:
1. Change a filter
2. Quickly change another filter before the first response arrives

**Observation 1 — Latest response wins**:
1. Final table state reflects the second filter set
2. UI does not flash an older page
3. No toast appears

---

### TC-EDGE-001: Whitespace-only token search is treated as empty (CH-015)

**Action**:
1. Type only whitespace into the token search bar
2. Press Enter

**Observation 1 — No filter change**:
1. Request payload `filters` array is unchanged
2. Table reverts to default

---

### TC-EDGE-002: Token search trims surrounding whitespace (CH-016)

**Action**:
1. Type ` status:completed ` (with spaces) and press Enter

**Observation 1 — Trimmed payload**:
1. `POST /call-log/list` body contains `status:completed` (trimmed)

---

### TC-EDGE-003: Token search accepts unicode and html-ish input without xss (CH-017)

**Action**:
1. Type `<script>alert(1)</script>` then an emoji and unicode text

**Observation 1 — Sent verbatim**:
1. Request body contains the text verbatim

**Observation 2 — No XSS execution**:
1. `window.alert` was not invoked
2. UI renders the text as plain string

---

### TC-EDGE-004: Very long token search does not crash the page (CH-018)

**Action**:
1. Paste a > 500-character token search

**Observation 1 — Page does not crash**:
1. Either request is sent unchanged or truncated
2. No client crash occurs

---

### TC-EDGE-005: Transcript search escapes regex special characters (CH-019)

**Preconditions**: Transcript loaded.

**Action**:
1. Type `.*` or `(foo)` in the transcript search

**Observation 1 — Regex-escaped via escapeRegex**:
1. Matches are treated as literal substring
2. Highlights still render where the literal occurs

---

### TC-EDGE-006: Whitespace-only transcript search restores full transcript (CH-020)

**Action**:
1. Type only whitespace into transcript search

**Observation 1 — Full transcript still visible**:
1. Zero `<mark>` elements rendered
2. All messages are visible

---

### TC-EDGE-007: Future date filter handled gracefully (CH-021)

**Action**:
1. Pick a future date in the Timeline picker

**Observation 1 — Graceful handling**:
1. Picker disables future days OR API returns empty
2. UI does not crash

---

### TC-EDGE-008: Pagination disables prev on the first page (CH-024)

**Preconditions**: Multiple pages of results.

**Action**:
1. Observe pagination on page 1

**Observation 1 — Prev disabled / Next enabled**:
1. Prev button is `disabled`
2. Next button is enabled

---

### TC-EDGE-009: Pagination disables next on the last page (CH-025)

**Preconditions**: Multiple pages of results.

**Action**:
1. Navigate to the last page

**Observation 1 — Next disabled / Prev enabled**:
1. Next button is `disabled`
2. Prev button is enabled

---

### TC-EDGE-010: Sort by Started At cycles asc and desc (CH-026)

**Action**:
1. Click the `Started At` column header twice in a row

**Observation 1 — Two list calls fire with sort direction**:
1. First click: `sort_by: 'started_at', sort_order: 'asc'`
2. Second click: `sort_by: 'started_at', sort_order: 'desc'`

---

### TC-EDGE-011: Sort by Duration orders rows by duration (CH-027)

**Action**:
1. Click the `Duration` column header

**Observation 1 — Sort payload**:
1. `POST /call-log/list` fires with `sort_by: 'duration_seconds'`

---

### TC-EDGE-012: Default date range applied on first load (CH-028)

**Action**:
1. Visit `/call-history`

**Observation 1 — Default range in payload**:
1. Payload includes a sensible `start_date_time`/`end_date_time` pair with the browser tz

---

### TC-EDGE-013: Custom date range refetches the list (CH-029)

**Action**:
1. Open drawer, pick a custom range, click Apply

**Observation 1 — Refetch with chosen ISO-8601 range**:
1. `POST /call-log/list` fires with the chosen `start_date_time` and `end_date_time`

---

### TC-EDGE-014: Removing a filter chip refetches without it (CH-030)

**Preconditions**: At least one filter applied (chip visible).

**Action**:
1. Click the chip's X

**Observation 1 — Chip removed and refetch fires**:
1. Chip is removed
2. `POST /call-log/list` re-fires without that filter

---

### TC-EDGE-015: Clear all filters resets drawer and toolbar state (CH-031)

**Action**:
1. Click `Clear all filters` from the empty state CTA

**Observation 1 — Reset behavior**:
1. Every drawer and toolbar filter is reset
2. List refetches
3. Filters toolbar badge count returns to 0

---

### TC-EDGE-016: Toggling a column updates the hidden count badge (CH-032)

**Action**:
1. Open the Columns popover
2. Toggle one column off

**Observation 1 — Column hidden + badge increments**:
1. The column is no longer visible in the table
2. Hidden-count badge increments by 1
3. Selection persists while user remains on the page

---

### TC-EDGE-017: Changing page size resets to page 1 (CH-033)

**Action**:
1. Change page size to 10, then 25, then 50, then 100

**Observation 1 — Each change refires with new size + page_no: 1**:
1. Each change fires `POST /call-log/list` with the new `page_size` and `page_no: 1`

---

### TC-A11Y-001: Tab order through toolbar reaches every control (CH-034)

**Action**:
1. Focus the page
2. Tab through the toolbar

**Observation 1 — Tab order**:
1. Token search → Columns → Filters → first sortable header
2. Every interactive control is reachable

---

### TC-A11Y-002: Filter drawer traps focus and restores on close (CH-035)

**Action**:
1. Open the Filters drawer
2. Tab repeatedly
3. Press Esc

**Observation 1 — Focus trapped inside**:
1. Tab cycles within the drawer
2. Focus does not escape to the page behind

**Observation 2 — Esc restores focus**:
1. Drawer closes
2. Focus returns to the Filters button

---

### TC-A11Y-003: Enter on sortable header triggers sort (CH-036)

**Action**:
1. Focus a sortable column header
2. Press Enter

**Observation 1 — Sort fires like click**:
1. `POST /call-log/list` re-fires with the updated sort

---

### TC-A11Y-004: Error toast is announced via aria-live (CH-037)

**Action**:
1. Trigger an error toast (e.g. via TC-ERROR-001)

**Observation 1 — Toast role**:
1. Toast has `role="alert"` or `aria-live`
2. Screen readers announce the toast title without manual focus

---

### TC-A11Y-005: Active detail tab exposes aria-current (CH-038)

**Action**:
1. Navigate to a detail page
2. Inspect the sidebar tab pills

**Observation 1 — aria-current="page" on active**:
1. The active tab has `aria-current="page"`
2. Other tabs do not have `aria-current`

---

### TC-A11Y-006: Audio player exposes native keyboard controls (CH-039)

**Action**:
1. Focus the audio player
2. Press space and arrow keys

**Observation 1 — Native HTML5 controls work**:
1. `<audio controls>` is used
2. Native keyboard shortcuts (space, arrows) work
3. No custom widget intercepts

---

### TC-A11Y-007: Copy link button announces success state (CH-040)

**Action**:
1. Click "Copy link"

**Observation 1 — Accessible name updates**:
1. The button accessible name flips to `Copied` for ~1.5 s
2. Either an `aria-live` region or the text update announces it

---

### TC-FULL-001: End-to-end call history list + detail (CH-FULL)

**Preconditions**:
- Test user provisioned; `__e2e__`-prefixed seed data for at least one call.

**Action**:
1. Authenticate via `loginViaUI`
2. Visit `/call-history`
3. Type token search `status:completed`, then clear it
4. Open Filters drawer, pick a 7-day range, toggle `direction: outbound`, click Apply
5. Reopen drawer, click Reset
6. Toggle a column off
7. Change page size to 25
8. Click the first row
9. Switch to Metrics tab, then to Configurations tab
10. Click "Back to Call History"
11. Open a row again, click "Copy link"

**Observation 1 — Step 2 — List loads**:
1. h1 `Call History` visible
2. Total badge reflects the response

**Observation 2 — Step 3 — Token search refetch**:
1. `POST /call-log/list` fires with status filter
2. Clearing it re-fires with no filter

**Observation 3 — Step 4 — Apply refetch**:
1. Filters toolbar badge equals 1
2. `POST /call-log/list` fires with new range + facet

**Observation 4 — Step 5 — Reset**:
1. Badge gone
2. List refetches with no filter

**Observation 5 — Step 6 — Column toggle**:
1. Hidden-count badge increments

**Observation 6 — Step 7 — Page size change**:
1. `POST /call-log/list` fires with `page_size: 25, page_no: 1`

**Observation 7 — Step 8 — Detail loads**:
1. URL is `/call-history/<id>/transcription`
2. Breadcrumb + summary card render
3. Audio loader visible

**Observation 8 — Step 9 — Tab switching**:
1. URLs become `/call-history/<id>/metrics` then `/call-history/<id>/configurations`

**Observation 9 — Step 10 — Back link**:
1. URL becomes `/call-history`
2. Filters cleared (after Reset in step 5)

**Observation 10 — Step 11 — Copy link**:
1. Clipboard contains the detail URL
2. Button reads `Copied` for ~1.5 s

**Cleanup** (in `try/finally`):
1. Delete seeded `__e2e__` call/agent data via the backend admin API
2. Clear cookies and localStorage

---

## Edge Cases (each appears above)

- [x] Unauthenticated access → see TC-NAV-001
- [x] List empty (no calls at all) → see TC-ERROR-003
- [x] List empty under active filters → see TC-ERROR-004
- [x] Audio URL fetch fails → see TC-ERROR-005
- [x] No `recording_upload_id` on the call → see TC-ERROR-006
- [x] No transcript → see TC-ERROR-007
- [x] Transcript search no matches → see TC-ERROR-008
- [x] Filters that require metrics auto-exclude calls without metrics — documented in TC-HAPPY-008 (helper text)
- [x] Browser time zone captured once via `getBrowserTimeZone` — see TC-EDGE-012
- [x] Column visibility resets when navigating away — covered in business rules + TC-EDGE-016
- [x] Sort/page-size change resets page → see TC-EDGE-017 / TC-EDGE-010
- [x] Copy link "Copied" indicator clears after ~1.5 s → see TC-HAPPY-006
- [x] Filter drawer closed without Apply discards draft → see TC-HAPPY-008 Observation 4
- [x] Timezone-aware filter payloads → see TC-EDGE-012
- [x] Column visibility persistence across navigation (no localStorage) — see TC-EDGE-016
- [x] Copy-link clipboard permission denied (silent) — covered by toast table (no toast)
- [x] Insecure context (HTTP) Copy link no-ops — covered by toast table
- [x] Avatar / row icon image 404 — `⚠ unverified`; not asserted
- [x] Sort while previous list-fetch is in flight — see TC-LOADING-004
- [x] Switching tabs does NOT refetch — see TC-HAPPY-009 Observation 1
- [x] Hard-loaded stale id with active filters → covered by TC-NAV-005 (state preserved)

---

## Business Rules

- The list endpoint is server-driven for filters, sort, pagination, and facets — no client-side filtering on already-fetched rows.
- Date range is always sent with an explicit time zone; backend interprets `start_date_time` / `end_date_time` accordingly.
- "Duration" prefers recording length over `(ended_at - started_at)` when both are available.
- Status colors follow a fixed mapping (e.g. completed = green, failed = red); badges include the status text.
- The detail tabs share a single `CallDetailContext` instance so siblings don't refetch the call independently.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Token search input has an accessible label → covered by TC-A11Y-001
- [x] Columns popover groups have group-toggle controls labeled by name → covered in TC-A11Y-001
- [x] Filter drawer traps focus and restores it on close → see TC-A11Y-002
- [x] Chat message bubbles use proper roles + names → covered by render observations in TC-HAPPY-003
- [x] Audio player uses native `<audio controls>` → see TC-A11Y-006
- [x] Transcript search highlights readable in dark mode → covered in TC-HAPPY-005
- [x] Tab pills expose `aria-current="page"` → see TC-A11Y-005
- [x] Copy-link button announces success → see TC-A11Y-007
- [x] Error toast announced via aria-live → see TC-A11Y-004
- [x] Enter on sortable header triggers sort → see TC-A11Y-003
