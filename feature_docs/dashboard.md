# Dashboard — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

The **Dashboard** is the home page of the Tone platform — the first screen a user lands on after login (`/home`). It surfaces four aggregate KPIs for the caller's organization (total agents, active calls, minutes used this month, success rate over the last 30 days) and a set of quick-link cards (Agents, Team Members, Integrations) for navigation.

It is a **read-only, single-endpoint feature**: a single `GET /api/v1/dashboard/stats` call returns the entire payload, computed live by `DashboardService.get_stats()` over the `agents` and `calls` tables. There is no dedicated dashboard table, no time-series storage, no caching, and no pre-aggregation.

- **Target users**: every authenticated user — this is the default landing page for all roles.
- **Problem solved**: gives the user an at-a-glance sense of platform activity (agents configured, voice traffic, monthly usage) without having to navigate to per-feature pages.

Cross-links: depends on [[agents]] (counts `agents.deleted_at IS NULL`) and the calls/voice pipeline (reads `calls.started_at` / `ended_at` / `duration_seconds`). See [[call-logs]] for the canonical call entity.

## 2. User stories & use cases

- As a **user landing on `/home`**, I want to see how many agents my org has configured so I know whether the workspace is set up.
- As an **org admin**, I want to see how many calls are happening right now ("Active Calls") so I can gauge real-time load.
- As an **org admin / billing owner**, I want to see total minutes consumed this calendar month so I can track usage against my plan.
- As an **operations user**, I want a success-rate KPI over the last 30 days so I can spot quality regressions.
- As **any user**, I want quick-link cards on the home page so I can jump to the most common destinations (Agents, Members, Integrations) without using the sidebar.

Typical flow: User logs in → middleware redirects to `/home` → `HomePage` mounts → `fetchDashboardStatsAtom` fires once → renders four stat cards and three quick-link cards. While loading, every stat value renders as `—`.

## 3. Functional requirements

- **`GET /api/v1/dashboard/stats`** returns a flat object with exactly four numeric fields: `total_agents`, `active_calls`, `minutes_used`, `success_rate`. No nesting, no time series, no per-agent breakdown.
- **Scope**: every count is filtered to the caller's `organization_id` via `BaseService.query()` (which auto-applies `where organization_id == self.org_id` whenever the model declares it). Both `Agent` and `Call` are `OrgScopedModel` instances, so the filter is automatic.
- **Auth**: requires a JWT and org membership.
  - Core router: `Depends(require_org_member)` (`core/api/v1/dashboard.py`).
  - EE router: `Depends(require_ee_org_member)` (`ee/api/v1/dashboard.py`) — both delegate to the same `get_dashboard_stats_handler` in `core/api/v1/dashboard.py`.
- **Metric definitions** (per `core/services/dashboard_service.py`):
  - `total_agents` — `count(agents)` where `deleted_at IS NULL` (lifetime, not windowed).
  - `active_calls` — `count(calls)` where `ended_at IS NULL` AND `started_at >= now() - 1h`. The 1-hour cap prevents a stuck/crashed row with a missing hangup event from inflating the gauge forever.
  - `minutes_used` — `sum(coalesce(duration_seconds, 0)) / 60`, rounded to 1 decimal place, over rows with `started_at >= start of current calendar month (UTC)`.
  - `success_rate` — over rows with `started_at >= now() - 30d` AND `ended_at IS NOT NULL`: `(count where duration_seconds > 0) / count(all finished) * 100`, rounded to 1 decimal. Returns `0.0` when there are no finished calls in the window.
- **Frontend**: `/home` page renders four `Card` components driven by `statCards` config (label + key + suffix + icon) plus three quick-link cards (Agents, Team Members, Integrations) and a primary "Create Agent" CTA linking to `/agents`.
- **In-flight de-dupe**: `fetchDashboardStatsAtom` uses a module-scoped `inFlight: Promise | null` guard so React 19 Strict Mode double-mount, sibling subscribers, and re-render-triggered setter calls all share the same in-flight request.

### Edge cases & failure modes

- Empty org: all four metrics return `0` (`total_agents=0`, `active_calls=0`, `minutes_used=0.0`, `success_rate=0.0`). Never `null`.
- Loading state: while `inFlight` is true, frontend renders every stat value as `—` (an em-dash). No skeletons.
- Fetch failure: `handleApiError(error)` shows a toast; the atom's `stats` stays `null`, so the UI keeps showing `—`. There is **no retry** and **no error banner on the page** — only the toast.
- Stuck "active" calls older than 1h are intentionally excluded — they look "active" by `ended_at IS NULL` but the time window filters them out.
- `success_rate` divide-by-zero is handled by the `if finished_calls_30d > 0` branch — returns `0.0` rather than `null` or `NaN`.
- `minutes_used` uses **calendar month UTC** boundary. ⚠ Users in non-UTC timezones near month rollover may see "month-to-date" reset based on UTC, not local time.
- ⚠ **Pipeline cut-over warning** (from `dashboard_service.py` docstring): "the live voice pipeline does not yet write to `calls`; these metrics will report 0 until the pipeline cut-over lands." `active_calls`, `minutes_used`, and `success_rate` are effectively dead numbers in Core today.
- ⚠ **No time-range parameter**: the endpoint hard-codes "last 30 days" for `success_rate`, "current calendar month" for `minutes_used`, "1 hour" for active. Users cannot pick a window.
- ⚠ **No per-agent breakdown**: the response is org-wide only.
- ⚠ **No caching**: every page load runs 4 SQL queries (1 for agents + 3 for calls). With no index on `calls.started_at`, this will seq-scan as the calls table grows.
- ⚠ **Soft-delete filter on calls is missing**: `Call` is `OrgScopedModel`, so it may have a `deleted_at` column, but the service does not filter on it. If `Call.deleted_at` exists, soft-deleted calls leak into all three call-derived metrics.
- ⚠ **No e2e coverage**: no test exercises the live `/dashboard/stats` endpoint end-to-end.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `BaseService.query()` which auto-injects `where organization_id == self.org_id`. Cross-org leakage is structurally prevented.
- **RBAC**: ⚠ **Not enforced beyond "is an org member"**. There is no `require_permission("dashboard:read")` or role check.
- **Performance**:
  - 4 sequential SQL count/sum queries per request. No batching.
  - ⚠ No index on `calls.started_at` despite three of the four metrics filtering by it.
  - ⚠ No caching. Every dashboard load on every tab refetches.
- **Observability**: no metrics, no structured logging, no cache-hit tracking. Failure path only shows a toast to the user.
- **Resilience**: no retry on the frontend; no circuit breaker.

## 5. Test cases (as-built)

There is **no dedicated test file** for the dashboard feature in this codebase. The block below is the **locked-in behavior** the code currently encodes.

```
TEST: stats_empty_org
  GIVEN authenticated user in org A with 0 agents and 0 calls
  WHEN  GET /api/v1/dashboard/stats
  THEN  200; body = {total_agents: 0, active_calls: 0, minutes_used: 0.0, success_rate: 0.0}

TEST: stats_counts_agents_excluding_soft_deleted
  GIVEN org A has 3 agents (1 with deleted_at set)
  WHEN  GET /dashboard/stats
  THEN  total_agents == 2

TEST: stats_active_calls_within_window
  GIVEN org A has 1 call started 5 minutes ago with ended_at=NULL
        AND     1 call started 2 hours ago with ended_at=NULL (orphan)
        AND     1 call started 5 minutes ago with ended_at set
  WHEN  GET /dashboard/stats
  THEN  active_calls == 1

TEST: stats_minutes_used_month_boundary
  GIVEN current month-to-date has 2 calls of 90s and 30s
        AND prior month has a 600s call
  WHEN  GET /dashboard/stats
  THEN  minutes_used == 2.0

TEST: stats_success_rate_zero_when_no_finished_calls
  GIVEN no calls with ended_at in last 30 days
  WHEN  GET /dashboard/stats
  THEN  success_rate == 0.0

TEST: stats_success_rate_ratio
  GIVEN last 30 days: 10 calls with ended_at set, 8 with duration_seconds > 0
  WHEN  GET /dashboard/stats
  THEN  success_rate == 80.0

TEST: stats_cross_org_isolation
  GIVEN org A has 5 agents, org B has 0 agents
  WHEN  GET /dashboard/stats as user from org B
  THEN  total_agents == 0

TEST: stats_requires_auth
  WHEN  GET /dashboard/stats without bearer token
  THEN  401
```

## 6. Data model / DB schema

**No dedicated dashboard table.** The feature is a pure read aggregation over two existing tables — `agents` and `calls`. Nothing is persisted by this endpoint. No migrations are owned by this feature.

| Table    | Columns referenced                              | Notes                                                |
|----------|-------------------------------------------------|------------------------------------------------------|
| `agents` | `organization_id`, `deleted_at`                 | Counted with soft-delete filter applied              |
| `calls`  | `organization_id`, `started_at`, `ended_at`, `duration_seconds` | All three call-derived metrics scan this table |

**Indexes the feature would benefit from** (not currently present):
- ⚠ `ix_calls_org_started_at` on `(organization_id, started_at)` — every call-derived metric filters by both.
- ⚠ Partial index on `calls(organization_id) WHERE ended_at IS NULL` — would make the active-calls count an index-only scan.

**Pre-aggregation**: none. There is no Celery task that rolls up dashboard numbers.

## 7. API design

All endpoints under prefix `/api/v1/dashboard`. Auth: JWT bearer. RBAC: ⚠ only `require_org_member`.

| Method | Path                  | Purpose                                          | Source                              |
|--------|-----------------------|--------------------------------------------------|-------------------------------------|
| GET    | `/dashboard/stats`    | Org-wide aggregate KPIs for the home page        | `core/api/v1/dashboard.py` (Core) + `ee/api/v1/dashboard.py` (EE) |

Both routers delegate to the same shared handler `get_dashboard_stats_handler(claims, db)` in `core/api/v1/dashboard.py`.

**Response shape** (`200 OK`)
```json
{
  "total_agents": 5,
  "active_calls": 2,
  "minutes_used": 1250.4,
  "success_rate": 94.5
}
```

- All four fields are always present.
- `total_agents` and `active_calls` are integers.
- `minutes_used` and `success_rate` are floats rounded to 1 decimal place.

### ⚠ Not implemented

- No `?days=N` window parameter.
- No per-agent breakdown endpoint.
- No time-series endpoint.
- No cost / latency / token metrics.
- No cache headers (`Cache-Control`, `ETag`).

## 8. Backend implementation

- **Controller**: `core/api/v1/dashboard.py` — 23 lines.
  - `get_dashboard_stats_handler(claims, db)` — shared handler.
  - `GET /stats` — thin router binding with `require_org_member` auth dep.
- **EE controller**: `ee/api/v1/dashboard.py` — 17 lines. Imports `get_dashboard_stats_handler` from Core, re-binds under `require_ee_org_member`.
- **Service**: `core/services/dashboard_service.py` — `DashboardService(BaseService)` with a single `get_stats() -> dict` method. Uses `func.coalesce(func.sum(...), 0)` to make the sum NULL-safe.
- **Models read**: `core.models.agent.Agent`, `core.models.call.Call`.
- **No Celery tasks**, no audit logging (read-only), no Pydantic response model.

## 9. Frontend implementation

- **Route**: `/home` — `frontend/src/app/(dashboard)/home/page.tsx`. Wrapped in the `(dashboard)` route group. The root `/` redirects to `/home`.
- **API service**: `frontend/src/services/dashboardService.ts` — `DashboardStats` interface + `getDashboardStats()` function.
- **State (Jotai)**: `frontend/src/atoms/DashboardAtom.tsx` — `dashboardAtom` ({stats, loading}) + `fetchDashboardStatsAtom` (write-only async atom with module-scoped `inFlight` guard for cross-subscriber de-dupe).
- **UI** (`HomePage`):
  - Header: "Welcome to Tone" + subhead + primary "Create Agent" CTA.
  - Four stat cards driven by `statCards` config — each with label, key, suffix, subtitle, icon (lucide-react).
  - While `loading || !stats`, every stat value renders as `—`.
  - Three quick-link cards: Agents, Team Members, Integrations.
- **Polling / auto-refresh**: ⚠ **None**. Numbers are stale from render until navigate-away.

## 10. Postman collection & examples

Located at `postman_collection/dashboard.postman_collection.json`. Single request: **"Get Dashboard Stats"**.

### GET /api/v1/dashboard/stats

```bash
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/dashboard/stats"
```

**Response 200**
```json
{
  "total_agents": 5,
  "active_calls": 2,
  "minutes_used": 1250,
  "success_rate": 94.5
}
```

> ⚠ The Postman saved example shows `minutes_used: 1250` (integer), but the service returns a float rounded to 1 decimal. Cosmetic drift.

**Error responses**:
- `401 Unauthorized` — missing or invalid bearer token.
- `403 Forbidden` — token is valid but not an org member.

## 11. Next steps

- [ ] ⚠ **Verify the pipeline cut-over to `calls`**: the service docstring notes "the live voice pipeline does not yet write to `calls`". Until then, three of four metrics report 0.
- [ ] ⚠ **Add an index** on `calls(organization_id, started_at)`.
- [ ] ⚠ **Add Redis caching** to `/dashboard/stats` (TTL 30–60s).
- [ ] ⚠ **Confirm `Call.deleted_at` handling** if the column exists.
- [ ] ⚠ **Add RBAC**: wrap with `require_permission("dashboard:read")` when permission system lands.
- [ ] **Add a `?days=N` query param** for `success_rate` window.
- [ ] **Add `/dashboard/stats/by-agent`** endpoint for per-agent rollups.
- [ ] **Frontend**: consider auto-refresh on a 30–60s interval; add a skeleton state instead of em-dashes.
- [ ] **Add e2e coverage** at `frontend/e2e/dashboard/home.spec.ts`.
- [ ] **Add a backend test** under `core/tests/` covering §5.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) RBAC weak — only `require_org_member`; (2) pipeline cut-over to `calls` not yet complete per service docstring, so `active_calls` / `minutes_used` / `success_rate` may all report 0 in Core; (3) no index on `calls.started_at` despite three of four metrics filtering by it; (4) no caching at all; (5) no `?days=N` parameter — windows are hard-coded; (6) no per-agent breakdown; (7) `Call.deleted_at` may not be filtered in any of the three call-derived metrics; (8) Postman saved example shows `minutes_used` as an integer but service returns a 1-decimal float; (9) no auto-refresh on the frontend; (10) no test coverage in either backend or e2e suites.
