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

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.

---

### TC-HAPPY-001: Deep link loads full payload with stat cards + categories (WF-1 / PS-1)

**Preconditions**:
- Signed-in user; metrics row exists for `550e8400-call-001` with full payload as in PS-1.

**Action**:
1. Navigate to `/call-metrics/550e8400-call-001`

**Observation 1 — Network request**:
1. Exactly one `GET /call-metrics/550e8400-call-001` request is recorded

**Observation 2 — Loader → content transition**:
1. While in flight, the `AppLoader` is visible
2. Breadcrumb second crumb reads `Loading…`
3. After response, the loader is removed from the DOM

**Observation 3 — Breadcrumb + title**:
1. Breadcrumb reads `Call History / Acme Support Bot`
2. Page h1 title reads `Metrics — Acme Support Bot`

**Observation 4 — Four StatCards render**:
1. StatCard `Avg Latency` shows `1.2s` (computed from `user_bot_latency` mean)
2. StatCard `Turns` shows `2`
3. StatCard `LLM Tokens` shows `1,070` (formatted with `toLocaleString`)
4. StatCard `TTS Characters` shows `732`

**Observation 5 — Categories render**:
1. `Latency` category section is visible
2. `Usage` category section is visible

**API mock**: `GET /call-metrics/550e8400-call-001` → 200 with the full PS-1 body.

---

### TC-HAPPY-002: Toggle Chart ↔ Table on Turn Latency does not refetch (WF-2 / PS-3)

**Preconditions**: TC-HAPPY-001 just loaded; `turn_metrics` populated; `TurnLatencySection` visible.

**Action**:
1. Click the `Table view` button inside `TurnLatencySection`
2. Click the `Chart view` button

**Observation 1 — Active state flips to Table**:
1. The Table button has `aria-pressed="true"`
2. A `MetricsDataTable` replaces the chart

**Observation 2 — Active state flips back to Chart**:
1. The Chart button has `aria-pressed="true"`
2. The chart re-appears

**Observation 3 — No extra network calls**:
1. Zero additional `GET /call-metrics/*` requests fire during the toggling

---

### TC-HAPPY-003: Loading state renders AppLoader before payload arrives (PS-2)

**Preconditions**: Signed-in user; API delays the response 1 s.

**Action**:
1. Navigate to `/call-metrics/<id>`
2. Observe the initial frame

**Observation 1 — Title placeholder**:
1. Page title reads `Metrics` (no agent suffix yet)

**Observation 2 — Breadcrumb loading state**:
1. Second crumb text reads `Loading…`

**Observation 3 — Loader visible, content suppressed**:
1. `AppLoader` is visible
2. Zero `StatCard` elements are in the DOM yet

**API mock**: `GET /call-metrics/<id>` → 200 delayed 1 s with the PS-1 body.

---

### TC-HAPPY-004: Partial payload — only LLM usage section renders (PS-6)

**Preconditions**: Signed-in; metrics row has only `llm_usage` populated; `tts_usage`, `processing`, `turn_metrics`, `turns`, `user_bot_latency` are all empty.

**Action**:
1. Navigate to the call metrics page

**Observation 1 — Sections respect data presence**:
1. `LLMUsageSection` renders inside `Usage`
2. `TTSUsageSection` is NOT rendered
3. `Latency` category is NOT rendered (both `turn_metrics` and `processing` empty)

**Observation 2 — Stat cards**:
1. TTS Characters StatCard shows `0`
2. Avg Latency StatCard shows `-`

**API mock**: `GET /call-metrics/<id>` → 200 with `tts_usage=[]`, `processing=[]`, `turn_metrics=[]`, `turns=[]`, `user_bot_latency=[]`.

---

### TC-NAV-001: Unauthenticated visit redirects to login (CM-001 / WF-6)

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/call-metrics/<callId>`

**Observation 1 — Middleware redirect**:
1. Response status is 307
2. Final URL becomes `/auth/login?redirect=%2Fcall-metrics%2F<callId>`

---

### TC-NAV-002: Expired token redirects and clears cookie (CM-002)

**Preconditions**: Expired `tone_access_token` cookie.

**Action**:
1. Visit `/call-metrics/<callId>`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fcall-metrics%2F<callId>`

**Observation 2 — Cookie cleared**:
1. The expired cookie is no longer set after the login response

---

### TC-NAV-003: Back button pops history when available (WF-3 / PS-4 / CM-029)

**Preconditions**: User arrived at `/call-metrics/<id>` from `/call-history`; loaded.

**Action**:
1. Click the Back button (`aria-label="Back to call metrics"`)

**Observation 1 — router.back() invoked**:
1. URL reverts to `/call-history`

**Observation 2 — No toast**:
1. No Sonner toast appears

---

### TC-NAV-004: Back button falls back to /call-history on a fresh deep-link tab (CM-030)

**Preconditions**: Fresh tab; deep-linked directly to `/call-metrics/<id>`; `window.history.length <= 1`.

**Action**:
1. Click the Back button

**Observation 1 — router.push fallback**:
1. URL becomes `/call-history`

---

### TC-NAV-005: Breadcrumb `Call History` link returns to list (PS-5 / CM-031)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Click the `Call History` breadcrumb text

**Observation 1 — Navigation**:
1. URL becomes `/call-history`
2. The list page loads

---

### TC-NAV-006: Browser back leaves call-metrics with chart state ephemeral (CM-032)

**Preconditions**: TC-HAPPY-001 loaded; user has toggled Chart/Table on at least one section.

**Action**:
1. Press browser Back
2. Press browser Forward to return to `/call-metrics/<id>`

**Observation 1 — Returns to prior page**:
1. URL reverts to the prior page

**Observation 2 — Toggle state is ephemeral**:
1. After Forward, toggle state is reset to default (client-only state, not restored)

---

### TC-NAV-007: Reload re-fetches and renders metrics (CM-033)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Reload the page

**Observation 1 — Re-fires GET**:
1. Exactly one new `GET /call-metrics/<id>` request fires after reload
2. The page renders the same UI as TC-HAPPY-001

---

### TC-ERROR-001: 404 surfaces not-found toast and empty state (WF-4 / FS-1 / CM-007)

**Preconditions**: Signed-in; `<missingId>` has no metrics row.

**Action**:
1. Navigate to `/call-metrics/<missingId>`

**Observation 1 — Error toast**:
1. Toast title equals `Metrics not found for this call`
2. Toast variant is `error`

**Observation 2 — Empty state**:
1. Loader clears
2. Content area shows `No metrics found for this call.` centered
3. Zero StatCards render

**Observation 3 — Breadcrumb + title fallback**:
1. Breadcrumb falls back to `Call History / Detail`
2. Page title reads `Metrics` (no agent suffix)

**API mock**: `GET /call-metrics/<missingId>` → 404 `{"detail": "Metrics not found for this call"}`.

---

### TC-ERROR-002: 401 surfaces credentials toast (FS-2 / CM-005)

**Preconditions**: Stale `tone_access_token`.

**Action**:
1. Navigate to the page

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/<id>` → 401 `{"detail": "Could not validate credentials"}`.

---

### TC-ERROR-003: 403 surfaces forbidden toast (FS-3 / CM-003 / CM-006)

**Preconditions**: Signed-in but `tenant_id` header doesn't own the call.

**Action**:
1. Navigate to the page

**Observation 1 — Forbidden toast**:
1. Toast title equals `Forbidden`

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/<id>` → 403 `{"detail": "Forbidden"}`.

---

### TC-ERROR-004: 500 surfaces server error toast (FS-4 / CM-009)

**Action**:
1. Navigate to the page

**Observation 1 — Error toast**:
1. Toast title equals `Database connection error`

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/<id>` → 500 `{"detail": "Database connection error"}`.

---

### TC-ERROR-005: 400 surfaces detail toast (CM-004)

**Action**:
1. Navigate to a page where the API returns 400 for the path param

**Observation 1 — Toast surfaces backend detail**:
1. Toast title equals the backend `detail` string

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/<id>` → 400 `{"detail": "<backend message>"}`.

---

### TC-ERROR-006: 409 conflict surfaces toast (CM-008)

**Preconditions**: Legacy callId already migrated.

**Action**:
1. Navigate to the page

**Observation 1 — Conflict toast**:
1. Toast title equals the backend `detail` string

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/<id>` → 409 `{"detail": "Conflict"}`.

---

### TC-ERROR-007: 422 with array detail surfaces first msg (FS-8)

**Preconditions**: Path param coerces to whitespace `%20`.

**Action**:
1. Navigate to `/call-metrics/%20`

**Observation 1 — Toast surfaces first detail msg**:
1. Toast title equals the value of `detail[0].msg` via `handleApiError`'s array handling

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/%20` → 422 `{"detail": [{"loc":["path","call_id"],"msg":"..."}]}`.

---

### TC-ERROR-008: Network failure shows generic fallback toast then recovers on retry (FS-5 / CM-010)

**Preconditions**: Network unavailable for first request only.

**Action**:
1. Navigate to the page (first request fails)
2. Click a refresh affordance OR reload

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**Observation 3 — Retry resolves normally**:
1. Second `GET /call-metrics/<id>` returns 200
2. StatCards and categories now render

**API mocks**: first call `route.abort('failed')`; second call → 200 with PS-1 body.

---

### TC-LOADING-001: Slow metrics fetch keeps loader without spam (CM-011)

**Preconditions**: API delays response > 3 s.

**Action**:
1. Navigate to the page

**Observation 1 — Loader visible throughout**:
1. `AppLoader` is visible the entire 3 s+ window

**Observation 2 — Breadcrumb stays in loading state**:
1. Second crumb reads `Loading…` for the duration

**Observation 3 — No toast spam**:
1. Zero Sonner toasts appear during the wait

---

### TC-LOADING-002: Rapid navigation aborts older requests cleanly (WF-5 / FS-9 / FS-12 / CM-012)

**Preconditions**: Signed-in.

**Action**:
1. Open `/call-metrics/A` (request in flight)
2. Before A resolves, navigate to `/call-metrics/B`
3. Navigate back to `/call-metrics/A`

**Observation 1 — A's first request aborts cleanly**:
1. The first A request is cancelled (`controller.abort()`)
2. No Sonner toast appears for the aborted request

**Observation 2 — B request resolves**:
1. B's GET fires and renders normally

**Observation 3 — Second A request resolves last and renders**:
1. The newest A request resolves and renders into the page
2. No double-render flicker

---

### TC-EDGE-001: All-empty payload renders zeroed stat cards (FS-6 / CM-017)

**Preconditions**: API returns 200 with all arrays empty and scalars `null`.

**Action**:
1. Navigate to the page

**Observation 1 — Title + breadcrumb fallback**:
1. Title reads `Metrics`
2. Breadcrumb second crumb reads `Detail`

**Observation 2 — Stat cards show neutral defaults**:
1. Avg Latency = `-`
2. Turns = `0`
3. LLM Tokens = `0`
4. TTS Characters = `0`

**Observation 3 — Categories hidden**:
1. Neither `Latency` nor `Usage` category renders

**API mock**: `GET /call-metrics/<id>` → 200 with empty arrays and null scalars.

---

### TC-EDGE-002: Null array payload coerces without crash (FS-7 / CM-018)

**Preconditions**: Legacy backend returns arrays as `null`.

**Action**:
1. Navigate to the page

**Observation 1 — Defensive shim**:
1. `MetricsContent` coerces each `null` to `[]`
2. The page does NOT crash

**Observation 2 — Stat cards behave like all-empty payload**:
1. Avg Latency `-`, Turns `0`, LLM Tokens `0`, TTS Chars `0`

**API mock**: 200 with `llm_usage:null, tts_usage:null, user_bot_latency:null, turns:null, processing:null`.

---

### TC-EDGE-003: Null agent_name falls back to Detail / Metrics labels (CM-019)

**Preconditions**: 200 response with `agent_name: null`.

**Action**:
1. Navigate to the page

**Observation 1 — Title fallback**:
1. Page title reads `Metrics` (no agent suffix)

**Observation 2 — Breadcrumb fallback**:
1. Breadcrumb shows `Call History / Detail`

---

### TC-EDGE-004: Stat cards never render NaN (CM-021 / FS-10)

**Preconditions**: Payload has `llm_usage[i].total_tokens = undefined`.

**Action**:
1. Navigate to the page

**Observation 1 — No NaN in StatCards**:
1. LLM Tokens StatCard text contains only digits + commas, never the substring `NaN`
2. TTS Characters StatCard text contains only digits + commas, never `NaN`

> ⚠ unverified — confirm `MetricsContent` guards against undefined.

---

### TC-EDGE-005: Whitespace-only callId surfaces validation error (CM-013)

**Action**:
1. Visit `/call-metrics/%20`

**Observation 1 — Error toast**:
1. Toast title equals the backend's first `detail.msg` value

**Observation 2 — Empty state**:
1. Content shows `No metrics found for this call.`

**API mock**: `GET /call-metrics/%20` → 422 or 404 with `detail`.

---

### TC-EDGE-006: Special-character callId is rejected without xss (CM-014)

**Action**:
1. Visit `/call-metrics/<callId-with-html-and-emoji>`

**Observation 1 — Backend returns 404**:
1. Toast title equals `Metrics not found for this call`

**Observation 2 — No XSS execution**:
1. No script from the path is executed
2. The callId is rendered as text (if anywhere)

---

### TC-EDGE-007: Very long callId does not crash the page (CM-015)

**Action**:
1. Visit `/call-metrics/<callId longer than 500 chars>`

**Observation 1 — Page does not crash**:
1. Either the API returns 404 (toast `Metrics not found for this call`) or 414
2. The empty state still renders

---

### TC-EDGE-008: Rapid chart-table toggling does not refetch (CM-016)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Click Chart/Table toggle 10 times rapidly

**Observation 1 — Deterministic view**:
1. View flips deterministically; final state matches the last click

**Observation 2 — No extra API calls**:
1. Zero additional `GET /call-metrics/*` requests fire
2. No visual flicker between toggles

---

### TC-EDGE-009: Empty pathname segment renders Next.js 404 (FS-11)

**Action**:
1. Visit `/call-metrics/` (no callId)

**Observation 1 — Route does not match**:
1. Next.js renders the 404 page
2. Zero `GET /call-metrics/*` requests fire

---

### TC-EDGE-010: handleApiError swallows AbortError (FS-12)

**Preconditions**: Signed-in.

**Action**:
1. Navigate to `/call-metrics/<id>`
2. Before the request resolves, navigate away

**Observation 1 — No toast for abort**:
1. Zero Sonner toasts appear
2. `controller.signal.aborted || cancelled` guard short-circuits before `handleApiError`

---

### TC-A11Y-001: Tab order through metrics page reaches every control (CM-022)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Focus the Back button
2. Press Tab repeatedly through the page

**Observation 1 — Tab order**:
1. Order is: Back button → breadcrumb link → first ChartTableToggle (Chart button → Table button) → next section toggles
2. Every interactive control is reachable

---

### TC-A11Y-002: Keyboard activates the Back button (CM-023)

**Preconditions**: Back button is focused.

**Action**:
1. Press Enter (or Space)

**Observation 1 — Same as click**:
1. `useGoBack('/call-history')` fires
2. URL changes the same way as a mouse click

---

### TC-A11Y-003: Chart-Table toggle is keyboard and screen-reader accessible (CM-024)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Inspect a `ChartTableToggle` element

**Observation 1 — Role and label**:
1. Container has `role="group"`
2. Container has `aria-label="Chart or table view"`

**Observation 2 — Per-button state**:
1. The active button has `aria-pressed="true"`
2. The inactive button has `aria-pressed="false"`

---

### TC-A11Y-004: Enter on focused toggle button flips view (CM-025)

**Preconditions**: Toggle button is focused.

**Action**:
1. Press Enter

**Observation 1 — View flips**:
1. The active toggle flips to the focused option
2. `aria-pressed` updates accordingly

**Observation 2 — No extra fetch**:
1. Zero new `GET /call-metrics/*` requests fire

---

### TC-A11Y-005: Error toast is announced via aria-live (CM-026)

**Preconditions**: API returns 500.

**Action**:
1. Navigate to the page

**Observation 1 — Toast role**:
1. The toast container has `role="alert"` or `aria-live`
2. Screen readers announce the toast title without manual focus

---

### TC-A11Y-006: Breadcrumb is a labeled nav landmark (CM-027)

**Action**:
1. Inspect the breadcrumb element

**Observation 1 — Nav role + label**:
1. Element is `<nav aria-label="Breadcrumb">`
2. Screen readers expose it as a breadcrumb landmark

---

### TC-A11Y-007: Loader announces busy state to screen readers (CM-028)

**Action**:
1. Navigate to the page while the request is in flight

**Observation 1 — Busy attribute**:
1. The `AppLoader` exposes either `role="status"` or `aria-busy="true"`

> ⚠ unverified — confirm `AppLoader` implementation.

---

### TC-FULL-001: End-to-end per-call metrics lifecycle (CM-FULL)

**Preconditions**:
- A real call seeded via `__e2e__` agent + Call History flow; metrics ingested.

**Action**:
1. Drive a real call via the Call History flow (`__e2e__` seeded data)
2. Wait for metrics ingestion
3. Deep-link to `/call-metrics/<callId>`
4. Toggle every section between Chart and Table view
5. Click the Back button
6. From a fresh tab, deep-link the page again
7. Click the breadcrumb `Call History`

**Observation 1 — Step 3 — Loader → content**:
1. `AppLoader` is visible briefly
2. Breadcrumb + four stat cards + Latency/Usage categories render

**Observation 2 — Step 4 — All toggles work**:
1. Each section's `aria-pressed` flips correctly between Chart and Table

**Observation 3 — Step 5 — Back button restores list**:
1. URL becomes `/call-history`

**Observation 4 — Step 6 — Fresh tab deep link**:
1. URL is the deep link
2. The page loads with the same UI

**Observation 5 — Step 7 — Breadcrumb returns to list**:
1. URL becomes `/call-history`

**Cleanup** (in `try/finally` in the same test body):
1. Delete the seeded call/agent via the backend admin API
2. Clear cookies and localStorage

---

## Edge Cases (each appears as a `TC-EDGE-*` / `TC-LOADING-*` / `TC-NAV-*` / `TC-ERROR-*` test case above)

- [x] Unauthenticated access → see TC-NAV-001 (and `⚠ unverified` middleware note)
- [x] `agent_name = null` → see TC-EDGE-003
- [x] `user_bot_latency = []` → Avg Latency `-` covered in TC-EDGE-001
- [x] All metric arrays empty → see TC-EDGE-001
- [x] Legacy backend returns arrays as `null` → see TC-EDGE-002
- [x] `turn_metrics` present but none have `end_to_end != null` → covered by Turns logic in TC-HAPPY-001
- [x] Distinct LLM models concatenated in subtitle → covered in TC-HAPPY-001
- [x] React StrictMode double mount → covered by abort behavior in TC-LOADING-002 / TC-EDGE-010
- [x] Chart/Table preserves other section state → see TC-EDGE-008
- [x] Stat card values use `toLocaleString()` (en-US) → covered in TC-HAPPY-001
- [x] `animate-page` class applied → covered by render observations
- [x] No telemetry beyond the single GET → covered by network observations across happy/error cases
- [x] Chart Table toggle is keyboard-operable → see TC-A11Y-003 / TC-A11Y-004

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

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Breadcrumb nav uses `<nav aria-label="Breadcrumb">` → see TC-A11Y-006
- [x] Back button uses `aria-label="Back to call metrics"` → see TC-A11Y-002
- [x] Chart/Table toggle uses `role="group"` + `aria-label="Chart or table view"` → see TC-A11Y-003
- [x] Each toggle option exposes `aria-pressed` → see TC-A11Y-003 / TC-A11Y-004
- [x] AppLoader announces busy state → see TC-A11Y-007 (`⚠ unverified`)
- [x] Stat cards use semantic structure → covered by render observations
- [x] Section headings render as `<h2>` or styled equivalents → covered in TC-HAPPY-001
- [x] Empty state copy → covered in TC-ERROR-001..004
- [x] Color is not the sole indicator of meaning → covered by StatCard rendering
- [x] Error toast announced via aria-live → see TC-A11Y-005
