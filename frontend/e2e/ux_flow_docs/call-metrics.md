# Feature Doc: Call Metrics (Per-Call Detail)

Feature documentation for the standalone per-call metrics page at
`/call-metrics/[callId]`. Used by `/generate-tests call-metrics` (or `--docs
e2e/ux_flow_docs/call-metrics.md`) to ensure all user cases are covered.

Call Metrics is a deep-link friendly page that shows the latency, token, and
TTS-usage breakdown for a single call. It mirrors the Metrics tab inside the
Call History detail shell (`/call-history/[callId]/metrics`) but renders as
its own standalone route — entered directly from the Call Metrics analytics
table, a saved bookmark, or a deep link in an email/alert. Like the in-shell
Metrics tab, it reuses `MetricsContent` from
`src/components/call-history/metrics/`.

For the list view that drives users here, see the Call Metrics analytics
table (in the Call History area; the `/call-metrics/list` API powers it).

---

## Page

- **Route**: `/call-metrics/[callId]`
- **Wrapper**: `src/app/(dashboard)/call-metrics/[callId]/page.tsx`
- **Main component**: `src/components/call-metrics/CallMetricsDetailPage.tsx`
- **Reused components**:
  - `src/components/call-history/metrics/MetricsContent.tsx`
  - `src/components/call-history/metrics/StatCard.tsx`
  - `src/components/call-history/metrics/MetricsCategory.tsx`
  - `src/components/call-history/metrics/TurnLatencySection.tsx`
  - `src/components/call-history/metrics/ProcessingTimesSection.tsx`
  - `src/components/call-history/metrics/LLMUsageSection.tsx`
  - `src/components/call-history/metrics/TTSUsageSection.tsx`
  - `src/components/call-history/metrics/ChartTableToggle.tsx`
  - `src/components/shared/AppLoader`, `src/components/shared/CustomButton`
- **Service**: `src/services/callMetricsService.ts` (`getCallMetricsByCallId`)
- **Types**: `src/types/callMetrics.ts` (`CallMetricsDetail`, `CallMetricsRow`)
- **Hook**: `src/hooks/useGoBack.ts` (`useGoBack('/call-history')`)
- **Auth required**: yes (redirects to
  `/auth/login?redirect=%2Fcall-metrics%2F<callId>` when `tone_access_token`
  cookie is missing — `⚠ unverified` middleware match; the project's
  `(dashboard)` route group is gated, so this falls through automatically)

---

## User Stories

### US-1: Open a per-call metrics page via deep link

**As an** analyst, **I want to** open a metrics view for a specific call_id
without going through the Call History list, **so that** I can share links
to specific calls in alerts and reports.

**Acceptance criteria**:

- [ ] Visiting `/call-metrics/<callId>` triggers a single
      `GET /call-metrics/<callId>` request on mount
- [ ] While the request is in flight, the page renders the shared `AppLoader`
- [ ] Breadcrumb reads `Call History / <Agent Name>` once the response is
      available; while loading the second crumb is `Loading…`; if the API
      resolves with `agent_name = null` the crumb falls back to `Detail`
- [ ] Page heading is `Metrics — <Agent Name>` (or just `Metrics` when no
      agent name is available)

### US-2: See per-call stat cards + categories

**As an** analyst, **I want to** see four headline stat cards plus latency
and usage breakdowns, **so that** I can quickly judge call quality.

**Acceptance criteria**:

- [ ] Four `StatCard`s render at the top: Avg Latency (violet, `Gauge`),
      Turns (blue, `MessageSquare`), LLM Tokens (emerald, `BrainCircuit`),
      TTS Characters (amber, `Mic`)
- [ ] `Avg Latency` value is computed from `user_bot_latency[].latency`
      (mean, 1 decimal place, suffix `s`); shows `-` when array is empty
- [ ] `Turns` prefers `turn_metrics.filter(t => t.end_to_end != null).length`
      when `turn_metrics` is populated, else falls back to `turns.length`
- [ ] `LLM Tokens` aggregates `llm_usage[].total_tokens` and renders the
      distinct model names as the subtitle
- [ ] `TTS Characters` aggregates `tts_usage[].characters` and renders the
      first `tts_usage[0].model` as the subtitle when present
- [ ] A `Latency` category renders only when `turn_metrics.length > 0` OR
      any processing row has `model && value > 0`
- [ ] A `Usage` category renders only when `llm_usage.length > 0` OR
      `tts_usage.length > 0`

### US-3: Toggle chart and table views per section

**As a** power user, **I want to** flip any latency/usage section between
chart and table view, **so that** I can read raw values when needed.

**Acceptance criteria**:

- [ ] Each metric sub-section renders a `ChartTableToggle` (segmented
      `BarChart3` + `Table` icons, `role="group"`)
- [ ] The active toggle reflects `aria-pressed="true"` and a `bg-background`
      style; the inactive button uses `text-muted-foreground`
- [ ] Toggling does not refetch — state is purely client-side per section

### US-4: Navigate back to Call History

**As an** analyst, **I want to** return to the previous list,
**so that** I can pick another call.

**Acceptance criteria**:

- [ ] An `ArrowLeft` text-style `CustomButton` sits left of the title with
      `aria-label="Back to call metrics"`
- [ ] Clicking it uses `useGoBack('/call-history')`: pops history when
      `window.history.length > 1`, else `router.push('/call-history')`
- [ ] The breadcrumb `Call History` text is a `<Link href="/call-history">`
      and offers the same destination on click

### US-5: Handle a call_id with no metrics row

**As an** analyst, **I want to** see a clear empty state when the API
returns nothing, **so that** I know the call wasn't measured.

**Acceptance criteria**:

- [ ] When the request resolves but `detail` is still `null` (e.g. API
      returned an empty body or a network rejection was swallowed), the
      content area shows `No metrics found for this call.` in muted text
- [ ] When the request fails (non-abort), `handleApiError(error)` surfaces a
      Sonner toast and the page settles into the same `No metrics found for
      this call.` empty state

### US-6: Cancel in-flight fetch on fast navigation

**As a** user navigating quickly, **I want** stale requests to abort,
**so that** late responses don't overwrite my new page state.

**Acceptance criteria**:

- [ ] Mount uses an `AbortController`; unmount calls `controller.abort()`
- [ ] Axios cancel errors (`controller.signal.aborted` OR the `cancelled`
      closure flag) are swallowed — `handleApiError` is NOT called

---

## User Workflow Steps

Drives `frontend/e2e/dashboard/call-metrics.spec.ts`.

**WF-1: Deep link a call** (positive)
1. Authenticated user navigates to `/call-metrics/<callId>` → expected:
   `GET /call-metrics/<callId>` fires once; `AppLoader` visible.
2. Response resolves → expected: loader replaced by `MetricsContent`; four
   stat cards visible; breadcrumb updates to `Call History / <agent_name>`.
3. Title reads `Metrics — <agent_name>`.

**WF-2: Toggle chart ↔ table** (positive)
1. Response loaded; `TurnLatencySection` visible → expected: toggle group
   with `aria-label="Chart or table view"`.
2. User clicks the `Table view` button → expected: `aria-pressed="true"` on
   the Table option; the matching `MetricsDataTable` replaces the chart.
3. User clicks the `Chart view` button → expected: chart returns; no new API
   call observed.

**WF-3: Back navigation** (positive)
1. User clicks `ArrowLeft` button → expected: when prior history exists,
   `router.back()` fires; URL becomes the prior route.
2. Without prior history (direct deep link in a fresh tab) → expected:
   `router.push('/call-history')`; URL becomes `/call-history`.

**WF-4: Missing-metrics empty state** (negative)
1. User navigates to `/call-metrics/<missingId>` → expected:
   `GET /call-metrics/<missingId>` returns `404`.
2. `handleApiError` toast title `Metrics not found for this call` shown.
3. Loader clears; content area shows `No metrics found for this call.`
   centered text; no stat cards rendered.

**WF-5: Fast navigation aborts request** (positive)
1. User opens `/call-metrics/A` (request in flight) → before resolution,
   navigates to `/call-metrics/B` → expected: `A` request aborts cleanly;
   no toast; `B` request fires and resolves normally.

**WF-6: Auth-less deep link** (negative)
1. Unauthenticated user pastes `/call-metrics/<callId>` → expected:
   middleware redirects to `/auth/login?redirect=%2Fcall-metrics%2F<callId>`
   based on the missing `tone_access_token` cookie (`⚠ unverified` exact
   middleware match — confirm in `src/middleware.ts`).

---

## Input Specifications

The page itself accepts no user input fields (no forms, no search).
URL parameter only.

| Field   | Source       | Required | Validation              | Exact Error                          |
| ------- | ------------ | -------- | ----------------------- | ------------------------------------ |
| callId  | URL path     | Yes      | Non-empty string; UUID-like accepted but not enforced client-side | API `404 { "detail": "Metrics not found for this call" }` when unknown |

In-page controls (no validation, client-only state):

| Control            | Type    | Behavior                                          |
| ------------------ | ------- | ------------------------------------------------- |
| Chart/Table toggle | Segmented buttons | One per metric sub-section; toggles client view |
| Back button        | IconButton | History pop with fallback to `/call-history`  |

---

## Success Scenarios

**PS-1: Full per-sample payload loads**
- Preconditions: signed-in user; metrics row exists for the call.
- Steps: navigate to `/call-metrics/550e8400-call-001`.
- Expected: loader → four StatCards (Avg Latency `1.2s` ⚠ values depend on
  sample data, Turns `2`, LLM Tokens `1,070`, TTS Chars `732`); Latency
  category with `TurnLatencySection` only if `turn_metrics` non-empty,
  otherwise hidden; Usage category with LLM + TTS sections.
- **Mock API**: `GET /call-metrics/550e8400-call-001` →
  ```json
  {
    "id": "9c1f0b6e-3a2d-4b8e-91c2-7c8c1c4a8f01",
    "call_id": "550e8400-call-001",
    "agent_id": "agent-uuid",
    "agent_name": "Acme Support Bot",
    "started_at": "2026-06-08T14:22:10+00:00",
    "ended_at": "2026-06-08T14:25:55+00:00",
    "duration_seconds": 225,
    "avg_ttfb_ms": 312.5,
    "avg_latency_s": 1.245,
    "total_tokens": 1840,
    "total_tts_chars": 1276,
    "turn_count": 14,
    "ttfb": [{ "turn": 1, "value": 305.2 }, { "turn": 2, "value": 319.8 }],
    "processing": [{ "turn": 1, "value": 142.0 }, { "turn": 2, "value": 138.5 }],
    "llm_usage": [
      { "turn": 1, "model": "gpt-4o-mini", "prompt_tokens": 412, "completion_tokens": 78, "total_tokens": 490 },
      { "turn": 2, "model": "gpt-4o-mini", "prompt_tokens": 488, "completion_tokens": 92, "total_tokens": 580 }
    ],
    "tts_usage": [
      { "turn": 1, "model": "eleven_turbo_v2", "characters": 320 },
      { "turn": 2, "model": "eleven_turbo_v2", "characters": 412 }
    ],
    "user_bot_latency": [
      { "turn": 1, "latency": 1.18 },
      { "turn": 2, "latency": 1.31 }
    ],
    "turns": [
      { "role": "agent", "text": "Hi, this is Acme. How can I help?" },
      { "role": "user", "text": "I need to reschedule my appointment." }
    ]
  }
  ```

**PS-2: Loading state renders shared AppLoader**
- Preconditions: signed-in; API delays the response 1s.
- Steps: navigate, observe initial frame.
- Expected: title `Metrics`, breadcrumb second crumb `Loading…`,
  `AppLoader` visible, no `StatCard` rendered yet.
- **Mock API**: `GET /call-metrics/<id>` delayed; same 200 body as PS-1.

**PS-3: Toggle to Table view on Turn Latency**
- Preconditions: PS-1 loaded; `turn_metrics` populated.
- Steps: click the `Table view` button inside `TurnLatencySection`.
- Expected: button has `aria-pressed="true"`; `MetricsDataTable` replaces
  the chart; no extra API call.

**PS-4: Back button — history available vs deep link**
- Preconditions A: user arrived from `/call-history` — clicking
  `ArrowLeft` runs `router.back()` and URL reverts to `/call-history`.
- Preconditions B: fresh tab, deep link — clicking `ArrowLeft` runs
  `router.push('/call-history')`.
- Expected: no toast in either branch.

**PS-5: Breadcrumb agent link**
- Preconditions: PS-1 loaded.
- Steps: click the `Call History` breadcrumb text.
- Expected: navigation to `/call-history`; list page loads.

**PS-6: Partial payload — only LLM usage**
- Preconditions: signed-in; metrics row missing TTS arrays.
- Steps: navigate.
- Expected: only `LLMUsageSection` renders inside `Usage`; no `TTSUsageSection`;
  TTS stat card shows `0` characters; `Latency` category hidden if both
  `turn_metrics` and `processing` are empty.
- **Mock API**: as PS-1 but `tts_usage = []`, `processing = []`,
  `turn_metrics = []`, `turns = []`, `user_bot_latency = []`.

---

## Failure Scenarios

**FS-1: 404 — metrics not found**
- Preconditions: signed-in; call_id has no metrics row.
- Steps: navigate to `/call-metrics/unknown-id`.
- **Mock API**: `GET /call-metrics/unknown-id` →
  `404 { "detail": "Metrics not found for this call" }`
- Expected UI: error toast `Metrics not found for this call`; loader clears;
  content shows `No metrics found for this call.`; breadcrumb falls back to
  `Call History / Detail`; title `Metrics` (no agent suffix).

**FS-2: 401 — token expired**
- Preconditions: stale `tone_access_token`.
- **Mock API**: `GET /call-metrics/<id>` →
  `401 { "detail": "Could not validate credentials" }`
- Expected UI: error toast `Could not validate credentials`; empty state
  copy `No metrics found for this call.`; next client-side nav triggers the
  middleware redirect to `/auth/login` (`⚠ unverified` for this exact
  route).

**FS-3: 403 — wrong org**
- Preconditions: signed-in but `tenant_id` header doesn't own the call.
- **Mock API**: `GET /call-metrics/<id>` →
  `403 { "detail": "Forbidden" }`
- Expected UI: error toast `Forbidden`; empty state copy `No metrics found
  for this call.`.

**FS-4: 500 — backend error**
- **Mock API**: `GET /call-metrics/<id>` →
  `500 { "detail": "Database connection error" }`
- Expected UI: error toast `Database connection error`; empty state copy
  `No metrics found for this call.`.

**FS-5: Network failure / offline**
- Preconditions: signed-in; network down.
- **Mock API**: `route.abort('failed')` for `GET /call-metrics/<id>`.
- Expected UI: `handleApiError` toast title
  `Something went wrong. Please try again.`; empty state copy
  `No metrics found for this call.`.

**FS-6: 200 with all-empty arrays**
- **Mock API**: `GET /call-metrics/<id>` →
  ```json
  {
    "id": "x", "call_id": "x", "agent_id": null, "agent_name": null,
    "started_at": null, "ended_at": null, "duration_seconds": null,
    "avg_ttfb_ms": null, "avg_latency_s": null, "total_tokens": null,
    "total_tts_chars": null, "turn_count": null,
    "ttfb": [], "processing": [], "llm_usage": [], "tts_usage": [],
    "user_bot_latency": [], "turns": []
  }
  ```
- Expected UI: title `Metrics` (no agent name); breadcrumb second crumb
  `Detail`; stat cards show `Avg Latency: -`, `Turns: 0`, `LLM Tokens: 0`,
  `TTS Characters: 0`; neither `Latency` nor `Usage` category rendered.

**FS-7: 200 with null arrays (legacy rows)**
- Preconditions: legacy backend row where arrays come back as `null`.
- **Mock API**: same as PS-1 but `llm_usage: null`, `tts_usage: null`,
  `user_bot_latency: null`, `turns: null`, `processing: null`.
- Expected UI: `MetricsContent` defensive shim coerces each `null` to `[]`;
  page does NOT crash; stat cards behave as FS-6.

**FS-8: 422 — malformed call_id path param**
- **Mock API**: `GET /call-metrics/%20` →
  `422 { "detail": [{ "loc": ["path", "call_id"], "msg": "..." }] }`
  (`⚠ unverified` — backend uses `str`, so 422 is unlikely; treat as
  400-class fallback).
- Expected UI: error toast with the first `detail[].msg` (per
  `handleApiError`'s array handling); empty state copy.

**FS-9: Rapid re-navigation aborts older request**
- Steps: open `/call-metrics/A`; before A resolves, click breadcrumb to
  `/call-history`, then re-navigate to `/call-metrics/B`.
- Expected UI: A's request `abort`s silently (no toast); B's request fires
  and renders normally; no double-render flicker.

**FS-10: Render error inside MetricsContent (e.g. divide-by-zero)**
- Preconditions: malformed `llm_usage[i].total_tokens = undefined`.
- Expected UI: shim does not coerce `undefined` inside objects; aggregates
  may render `NaN` (`⚠ unverified` — confirm `MetricsContent` guards).
  Add a regression check that StatCard `LLM Tokens` never contains the
  string `NaN`.

**FS-11: Reload with empty pathname segment**
- Steps: visit `/call-metrics/` (no callId).
- Expected: route does not match; Next.js renders 404 page; no API call.

**FS-12: handleApiError swallows AbortError**
- Steps: trigger a navigation away mid-request.
- Expected: no Sonner toast appears (the `controller.signal.aborted ||
  cancelled` guard short-circuits before `handleApiError`).

---

## Expected Toast Messages

Sourced from `src/utils/toast.tsx` + `src/utils/helpers.ts`.

| Trigger                                   | Toast title (= `detail`)                  | Variant |
| ----------------------------------------- | ----------------------------------------- | ------- |
| `GET /call-metrics/<id>` 404              | `Metrics not found for this call`         | error   |
| `GET /call-metrics/<id>` 401              | `Could not validate credentials`          | error   |
| `GET /call-metrics/<id>` 403              | `Forbidden`                               | error   |
| `GET /call-metrics/<id>` 500              | `Database connection error` (server msg)  | error   |
| `GET /call-metrics/<id>` network fail     | `Something went wrong. Please try again.` | error   |
| `GET /call-metrics/<id>` 422 (array)      | first `detail[0].msg` value               | error   |
| `GET /call-metrics/<id>` aborted          | (no toast)                                | —       |
| Back button click                         | (no toast)                                | —       |
| Chart/Table toggle                        | (no toast)                                | —       |

Toast assertion target: `page.locator('[data-sonner-toast]').first()` should
contain the exact `detail` string.

---

## UI Elements

| Element                  | Type            | Content / Label                                | Behavior                                       |
| ------------------------ | --------------- | ---------------------------------------------- | ---------------------------------------------- |
| Breadcrumb nav           | `<nav aria-label="Breadcrumb">` | `Call History / <crumb>`        | First crumb is a `<Link>` to `/call-history`   |
| Crumb fallback (loading) | text            | `Loading…`                                     | Shown until first API resolution                |
| Crumb fallback (no name) | text            | `Detail`                                       | Shown when `agent_name` is null after load     |
| Back button              | IconButton (`CustomButton type="text"`) | `ArrowLeft` icon       | `aria-label="Back to call metrics"`; uses `useGoBack('/call-history')` |
| Page title               | h1              | `Metrics — <Agent Name>` or `Metrics`          | Static after load                              |
| Loader                   | AppLoader       | Spinner                                        | Visible while `loading === true`               |
| Empty state              | text            | `No metrics found for this call.`              | Visible when `!loading && !detail`             |
| StatCard — Avg Latency   | Card            | Gauge icon, violet `bg-violet-500`             | `mean(user_bot_latency.latency).toFixed(1) + 's'` or `-` |
| StatCard — Turns         | Card            | MessageSquare icon, blue `bg-blue-500`         | Prefers `turn_metrics`-derived count, fallback `turns.length` |
| StatCard — LLM Tokens    | Card            | BrainCircuit icon, emerald `bg-emerald-500`    | Sum of `llm_usage.total_tokens` + model list subtitle |
| StatCard — TTS Chars     | Card            | Mic icon, amber `bg-amber-500`                 | Sum of `tts_usage.characters` + first model subtitle |
| Latency category         | section         | `Latency` heading                              | Renders only if `turn_metrics.length > 0` or processing has a real row |
| Usage category           | section         | `Usage` heading                                | Renders only if any usage row exists           |
| Turn Latency section     | chart + toggle  | per-turn end-to-end latency                    | `ChartTableToggle` for chart vs table          |
| Processing Times section | chart + toggle  | per-model processing ms                        | `ChartTableToggle` for chart vs table          |
| LLM Usage section        | chart + toggle  | per-model token bars                           | `ChartTableToggle` for chart vs table          |
| TTS Usage section        | chart + toggle  | per-model TTS character bars                   | `ChartTableToggle` for chart vs table          |
| Chart/Table toggle       | role=group      | `aria-label="Chart or table view"`             | Two segmented buttons (`aria-pressed`)         |

---

## Navigation

| Trigger                               | Destination                                                | Condition                              |
| ------------------------------------- | ---------------------------------------------------------- | -------------------------------------- |
| Visit `/call-metrics/<id>`            | Renders this page                                          | `tone_access_token` present            |
| Visit `/call-metrics/<id>` (no auth)  | `/auth/login?redirect=%2Fcall-metrics%2F<id>`              | Middleware (`⚠ unverified`)           |
| Click breadcrumb `Call History`       | `/call-history`                                            | Always                                 |
| Click Back button (history present)   | Previous route (`router.back()`)                           | `window.history.length > 1`            |
| Click Back button (deep link)         | `/call-history`                                            | No prior history entry                 |
| Click any Chart/Table toggle          | Same URL; section view state updates                       | Always                                 |
| 404 from API                          | Same URL; empty state rendered; toast shown                | Server returns `404`                   |

---

## API Contracts

| Endpoint                          | Method | Request   | Success Response                | Error Response               |
| --------------------------------- | ------ | --------- | ------------------------------- | ---------------------------- |
| `/call-metrics/{call_id}`         | GET    | —         | `CallMetricsDetail` JSON        | `{ "detail": "..." }`        |
| `/call-metrics/list`              | POST   | filters   | `{ data, total, page_no, page_size }` | `{ "detail": "..." }`  |

The page only consumes `GET /call-metrics/{call_id}`. The `POST /list`
endpoint powers the upstream Call Metrics list view (documented separately
in the Call History area).

Source: `postman_collection/Tone-API.postman_collection.json` → folder
`Call Metrics`.

### Example — `GET /call-metrics/{call_id}` (200)

```json
{
  "id": "9c1f0b6e-3a2d-4b8e-91c2-7c8c1c4a8f01",
  "call_id": "550e8400-call-001",
  "agent_id": "agent-uuid",
  "agent_name": "Acme Support Bot",
  "started_at": "2026-06-08T14:22:10+00:00",
  "ended_at": "2026-06-08T14:25:55+00:00",
  "duration_seconds": 225,
  "avg_ttfb_ms": 312.5,
  "avg_latency_s": 1.245,
  "total_tokens": 1840,
  "total_tts_chars": 1276,
  "turn_count": 14,
  "ttfb": [{ "turn": 1, "value": 305.2 }, { "turn": 2, "value": 319.8 }],
  "processing": [{ "turn": 1, "value": 142.0 }, { "turn": 2, "value": 138.5 }],
  "llm_usage": [
    { "turn": 1, "model": "gpt-4o-mini", "prompt_tokens": 412, "completion_tokens": 78, "total_tokens": 490 },
    { "turn": 2, "model": "gpt-4o-mini", "prompt_tokens": 488, "completion_tokens": 92, "total_tokens": 580 }
  ],
  "tts_usage": [
    { "turn": 1, "model": "eleven_turbo_v2", "characters": 320 },
    { "turn": 2, "model": "eleven_turbo_v2", "characters": 412 }
  ],
  "user_bot_latency": [
    { "turn": 1, "latency": 1.18 },
    { "turn": 2, "latency": 1.31 }
  ],
  "turns": [
    { "role": "agent", "text": "Hi, this is Acme. How can I help?" },
    { "role": "user", "text": "I need to reschedule my appointment." }
  ]
}
```

### Example — error bodies

- `404 { "detail": "Metrics not found for this call" }`
- `401 { "detail": "Could not validate credentials" }`
- `403 { "detail": "Forbidden" }`
- `500 { "detail": "Database connection error" }`

### Example — `POST /call-metrics/list` (200, summary view, abbreviated)

```json
{
  "data": [{
    "call_id": "550e8400-call-001",
    "agent_name": "Acme Support Bot",
    "duration_seconds": 225,
    "avg_ttfb_ms": 312.5,
    "avg_latency_s": 1.245,
    "total_tokens": 1840,
    "total_tts_chars": 1276,
    "turn_count": 14
  }],
  "total": 1, "page_no": 1, "page_size": 10
}
```

---

## Edge Cases

- [ ] Unauthenticated access → middleware redirect (`⚠ unverified` for the
      `/call-metrics/[callId]` path explicitly)
- [ ] `agent_name = null` → breadcrumb shows `Detail`; title shows `Metrics`
- [ ] `user_bot_latency = []` → Avg Latency stat reads `-`
- [ ] All metric arrays empty → neither `Latency` nor `Usage` category renders
- [ ] Legacy backend row returns arrays as `null` → defensive `Array.isArray`
      shim coerces to `[]`; no runtime crash
- [ ] `turn_metrics` present but no entries have `end_to_end != null` →
      Turns count falls back to 0 from filter; fallback to `turns.length`
      only triggers when `turn_metrics.length === 0`
- [ ] Distinct LLM models concatenated with `, ` in subtitle
      (`[...new Set(llm_usage.map(u => u.model))].join(', ')`)
- [ ] Mounting twice quickly (React StrictMode dev) → first effect aborts
      its controller during cleanup; no toast spam
- [ ] Toggling between Chart/Table preserves the section's other state
- [ ] Stat card values use `toLocaleString()` → 1234 → `1,234` in en-US
- [ ] Page applies the `animate-page` class for the dashboard fade-in animation
- [ ] No telemetry / analytics event fires beyond the single GET (verify in
      tests that no extra POSTs to `/analytics/*` happen)
- [ ] Chart Table toggle is keyboard-operable (Tab + Enter/Space because it
      wraps `CustomButton`, which renders `<button>`)

---

## Business Rules

- The metrics row is upserted by `CallLogService.complete_call` after the
  pipeline drains (per the Postman folder description). A 404 here means
  the call exists but the pipeline never completed metric ingestion (or the
  call_id is wrong).
- `POST /call-metrics/list` is the summary endpoint (scalars only) and is
  whitelisted to specific filter/sort fields (`agent_name`, `agent_type`,
  `started_at`, `ended_at`, `duration_seconds`, `call_id`, `llm_provider`,
  `llm_model`, `stt_provider`, `stt_model`, `tts_provider`, `tts_model`).
  The detail endpoint adds the six per-sample arrays.
- All metric aggregates are computed client-side in `MetricsContent` —
  backend `avg_latency_s`, `total_tokens`, `total_tts_chars` are NOT used by
  the stat cards; the page recomputes from the per-sample arrays.
- Org isolation is enforced via the `tenant_id` header (injected by
  `src/utils/axios.ts`). A call belonging to a different org returns 404
  (or 403, `⚠ unverified`) regardless of the call existing.

---

## Accessibility Requirements

- [ ] Breadcrumb nav uses `<nav aria-label="Breadcrumb">`
- [ ] Back button uses `aria-label="Back to call metrics"`
- [ ] Chart/Table toggle uses `role="group"` + `aria-label="Chart or table view"`
- [ ] Each toggle option exposes `aria-pressed` for the active state and an
      `aria-label` describing the view (`Chart view`, `Table view`)
- [ ] AppLoader announces a busy state (`⚠ unverified` — confirm component
      uses `role="status"` or `aria-busy`)
- [ ] Stat cards use semantic structure (label text + value text); icon-only
      visuals are decorative
- [ ] Section headings (`Latency`, `Usage`) appear as `<h2>` or styled
      equivalents and are keyboard-focusable via Tab order
- [ ] Empty state copy `No metrics found for this call.` is centered, muted,
      and announced by screen readers as plain body text (no live region —
      acceptable since the page transitions from loader → static empty)
- [ ] Color is not the sole indicator of meaning for stat cards — labels
      always render alongside the colored icon background

---

## Appended Scenarios (gap-fill, ID prefix `CM-`)

These rows extend the PS/FS coverage with auth/error-state/network/a11y/list-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `call-metrics.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-001 | Visit `/call-metrics/<callId>` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fcall-metrics%2F<callId>` | `unauthenticated visit redirects to login` |
| CM-002 | Visit `/call-metrics/<callId>` with an expired token | Middleware 307 → `/auth/login?redirect=%2Fcall-metrics%2F<callId>`; expired cookie cleared | `expired token redirects to login and clears cookie` |
| CM-003 | Logged-in non-member opens deep link to a call from another org | API 403 / 404; toast `Forbidden` or `Metrics not found for this call`; empty state rendered | `non-member is denied access to a foreign call deep link` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-004 | `GET /call-metrics/<id>` 400 (malformed callId path param) | Toast surfaces backend `detail`; empty state `No metrics found for this call.` | `metrics 400 surfaces detail toast and renders empty state` |
| CM-005 | Token expires after page load and before a future request fires | Toast `Could not validate credentials`; empty state | `mid-flow 401 surfaces error toast and keeps empty state` |
| CM-006 | 403 forbidden role (call belongs to a different org) | Toast `Forbidden`; empty state | `metrics 403 surfaces forbidden toast` |
| CM-007 | 404 — unknown callId | Toast `Metrics not found for this call`; empty state; breadcrumb falls back to `Detail` | `metrics 404 surfaces not-found toast` |
| CM-008 | 409 conflict (legacy callId already migrated) | Toast surfaces backend `detail`; empty state | `metrics 409 surfaces conflict toast` |
| CM-009 | 500 server error | Toast `Database connection error`; empty state | `metrics 500 surfaces server error toast` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-010 | Offline / network failure | Toast `Something went wrong. Please try again.`; empty state; subsequent retry resolves normally | `network failure surfaces toast then recovers on retry` |
| CM-011 | Slow `GET /call-metrics/<id>` (>3s) | `AppLoader` visible the whole time; breadcrumb second crumb reads `Loading…`; no toast | `slow metrics fetch keeps loader without spam` |
| CM-012 | Rapid navigation A → B → A while requests are in flight | A's first request aborts cleanly (no toast); B's resolves; second A's resolves last and renders | `rapid navigation aborts older requests cleanly` |

### Input edge cases (URL param)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-013 | callId with leading/trailing whitespace via URL encoding (`%20`) | Trimmed by the backend; 422 or 404 returned; toast surfaces detail | `whitespace-only callId surfaces validation error` |
| CM-014 | callId with HTML-injection / unicode chars | Sent verbatim; backend returns 404; toast `Metrics not found for this call`; no XSS execution | `special-character callId is rejected without xss` |
| CM-015 | callId longer than 500 chars | Either accepted (404) or backend 414; no client crash | `very long callId does not crash the page` |
| CM-016 | Chart/Table toggle clicked rapidly | View flips deterministically; no extra API call observed; no flicker | `rapid chart-table toggling does not refetch` |

### Backend payload edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-017 | Payload arrays all empty (200) | Stat cards show `-` / `0` / `0` / `0`; neither Latency nor Usage category renders | `all-empty payload renders zeroed stat cards` |
| CM-018 | Payload arrays are `null` (legacy rows) | Defensive shim coerces `null → []`; no crash; same UI as CM-017 | `null array payload coerces without crash` |
| CM-019 | `agent_name = null` after load | Title reads `Metrics`; breadcrumb shows `Detail` | `null agent_name falls back to default labels` |
| CM-020 | Partial payload — only LLM usage present | LLMUsageSection renders; TTSUsageSection hidden; TTS stat card shows `0` | `partial payload renders only available sections` |
| CM-021 | StatCard never renders `NaN` (regression) | After any payload, LLM Tokens / TTS Chars contain only digits + commas | `stat cards never render NaN for any payload` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-022 | Tab order across the page | Back button → breadcrumb link → first ChartTableToggle → next toggle — reachable in order | `tab order through metrics page reaches every control` |
| CM-023 | Press Enter / Space on the Back button | Triggers `useGoBack('/call-history')` just like a click | `keyboard activates the back button` |
| CM-024 | ChartTableToggle exposes `role="group"` + `aria-label="Chart or table view"` | Both buttons render with `aria-pressed` reflecting the active view | `chart-table toggle is keyboard and screen-reader accessible` |
| CM-025 | Press Enter on a focused toggle button | Active toggle flips; `aria-pressed` updates; no extra fetch | `Enter on toggle button flips view` |
| CM-026 | Toast error has `role="alert"` / aria-live | Screen readers announce the toast title without manual focus | `error toast is announced via aria-live` |
| CM-027 | Breadcrumb nav uses `<nav aria-label="Breadcrumb">` | Landmark exposed; screen readers announce breadcrumb structure | `breadcrumb is a labeled nav landmark` |
| CM-028 | AppLoader exposes a busy state | Either `role="status"` or `aria-busy="true"` while loading | `loader announces busy state to screen readers` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-029 | Back button when history exists | Pops history via `router.back()`; lands on the previous route | `back button pops history when available` |
| CM-030 | Back button on a fresh deep-link tab | `router.push('/call-history')`; URL changes to the list | `back button falls back to call history when no history` |
| CM-031 | Breadcrumb `Call History` link click | Navigates to `/call-history` | `breadcrumb link returns to list` |
| CM-032 | Browser back after toggling Chart/Table | Returns to the prior page; toggle state not restored (client-only state) | `browser back leaves call-metrics with chart state ephemeral` |
| CM-033 | Reload the metrics page | Re-fires `GET /call-metrics/<id>`; same UI re-renders | `reload re-fetches and renders metrics` |

### Full lifecycle (`CM-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CM-FULL | Drive a real call via the Call History flow (`__e2e__` seeded data) → wait for metrics ingestion → deep-link `/call-metrics/<callId>` → assert `AppLoader` then breadcrumb + four stat cards + Latency/Usage categories → toggle every section between Chart and Table view, asserting `aria-pressed` flips → click Back button → assert URL is `/call-history` → revisit via breadcrumb back from another tab → cleanup: delete the seeded call/agent via API in the same `try/finally` block | All sections render; toggles are keyboard accessible; back button + breadcrumb both restore the list; seeded data cleaned up in the same test body | `walks the entire per-call metrics flow end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| CM-001..003 | WF-6 (auth-less deep link) | Adds expired-token + non-member cases |
| CM-004..009 | FS-1..FS-4 | Standardises 400/401/403/404/409/500 paths |
| CM-010..012 | FS-5, FS-9 | Network resilience + rapid navigation explicit |
| CM-013..016 | (new) | Input edge cases for the URL param + rapid toggles |
| CM-017..021 | FS-6, FS-7, FS-10 | Promotes payload-shape edge cases to scenarios |
| CM-022..028 | Accessibility section | Promotes a11y bullets to scenarios |
| CM-029..033 | Navigation table | Adds reload + browser back/forward checks |
| CM-FULL | (new) | Single-test sweep that drives a real call and verifies metrics |
