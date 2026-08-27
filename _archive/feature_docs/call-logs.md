# Call Logs — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

**Call Logs** is the historical record of voice calls handled by the [[voice-pipeline]] — each call ends with a row in `calls` (and possibly an `Upload` row pointing to the R2-stored audio recording + transcript). The frontend `/call-history` page lets users browse, filter, and play back past calls.

⚠ **The `call_logs` router is currently disabled in `main.py:19`** with the comment "temporarily disabled (references dropped pre-v2 models)." Controller + service code still exist but are not mounted. The endpoints below describe the **intended** surface; they are not live in Core today.

- **Target users**: operators (review what happened on a call), agent owners (QA conversations), analysts (export for offline review).
- **Problem solved**: a queryable history of voice traffic with audio + transcript playback per call.

Cross-links: [[voice-pipeline]] (writes call rows at end), [[agents]] (each call has an agent_id), [[channels]] (call originates on a channel).

## 2. User stories & use cases

- As an operator, I want to browse the last 100 calls for my org with filters (agent, status, date range).
- As an operator, I want to click a row and see the transcript + audio player.
- As an agent owner, I want to download the audio recording for offline analysis.
- As an analyst, I want to filter by from/to phone number to see a specific caller's history.
- As a tester, I want to see which channel + agent handled a call so I can reproduce the test.

Typical flow: User → `/call-history` → list page → filters (agent, status, date) → click row → drawer with transcript + audio player + metrics.

## 3. Functional requirements

- **`GET /call-log/filter-values`**: returns unique values for filter dropdowns (agents, statuses, channels).
- **`POST /call-log/list`**: paginated list with `search`, `sort_by`, `filter_by` (status, agent_id, channel_id), `from_date`, `to_date`.
- **`GET /call-log/{call_id}`**: detail view with transcript, metrics, timing, agent + channel info.
- **`GET /call-log/{call_id}/audio-url`**: returns signed R2 URL for the audio file.
- **`GET /call-log/{call_id}/audio`**: streams the audio with range-request support (for `<audio>` element seeking).
- **Audio storage**: in R2 via `core/utils/storage.py` (presigned URLs + ranged GET).
- **Multi-tenancy**: scoped by `organization_id`.

### Edge cases & failure modes

- **⚠ Router disabled**: `main.py:19` comments out the include. ⚠ All endpoints below return 404 today.
- **⚠ Schema drift**: `core/services/call_log_service.py` imports `core.models.call_log.CallLog` which does not exist — the v2 model is `core.models.call.Call`. Service will `ImportError` at startup.
- **⚠ Schema drift on Upload**: service expects fields `r2_object_key`, `call_log_id`, `file_size_bytes` on `Upload`, but the v2 model has `file_path`, no `call_log_id`, no `file_size_bytes`.
- **⚠ Core controller doesn't pass `org_id` to service** — multi-tenancy relies on context-var fallback. EE controller does pass it explicitly.
- **⚠ No pagination clamping**: `page_no <= 0` and unbounded `page_size` are not validated.
- **⚠ No per-column operator allow-list**: `contains` filter can be applied to int columns — runtime errors.
- **⚠ No automated tests** for `/call-log/*`.
- **⚠ Postman drift**: collection samples use ISO strings (service wants epoch int) and nested `pagination` (service returns flat).
- **⚠ Transcript / audio recording are best-effort** in the pipeline — not mandatory. Some rows may have NULL transcript or NULL audio.
- **⚠ No audit logging** (but call rows are themselves an "audit trail" of voice traffic).
- **Pipeline write path**: `core/services/agent_factory_service.py` (lines 1280-1450) is the intended writer; verify it's wired.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `organization_id` on `calls` and `uploads`.
- **AuthN**: `require_org_member`.
- **RBAC**: ⚠ none.
- **Performance**: list endpoint paginates; no enforced limit on `page_size`.
- **Audio streaming**: range-request support to enable seeking in the `<audio>` element.
- **Audit logging**: ⚠ none.
- **EE parity**: `ee/api/v1/call_logs.py` mirrors core but correctly passes `org_id`.

## 5. Test cases (as-built)

⚠ **No tests** for `/call-log/*` endpoints.

```
TEST: list_filter_by_agent
  WHEN  POST /call-log/list {"filter_by":{"agent_id":"X"}}
  THEN  only calls where agent_id == X

TEST: list_filter_by_date_range
  WHEN  POST /call-log/list {"from_date":"2026-05-01","to_date":"2026-05-27"}
  THEN  calls with started_at in range

TEST: list_sort_by_duration_desc
  WHEN  POST /call-log/list {"sort_by":"-duration_seconds"}
  THEN  ordered by duration descending

TEST: get_call_log_with_transcript
  GIVEN call C with transcript persisted
  WHEN  GET /call-log/C
  THEN  200; body has transcript, audio_url, agent_id, channel_id, status, duration_seconds

TEST: audio_url_signed
  WHEN  GET /call-log/C/audio-url
  THEN  200; {"url": "https://r2.../signed?expires=..."}

TEST: audio_stream_range
  WHEN  GET /call-log/C/audio with Range: bytes=0-1023
  THEN  206 Partial Content; body has first 1024 bytes

TEST: cross_org_isolation
  GIVEN call C in org A; caller in org B
  WHEN  GET /call-log/C
  THEN  404

TEST: router_disabled_smoke
  GIVEN main.py has call_logs router commented out
  WHEN  POST /call-log/list
  THEN  ⚠ 404 — router not mounted

TEST: filter_values
  WHEN  GET /call-log/filter-values
  THEN  200; {"agents":[...], "statuses":["completed","failed","..."], "channels":[...]}
```

## 6. Data model / DB schema

**Table: `calls`** (`core/models/call.py`)

| Column            | Type        | Null | Default     | Notes                                                |
|-------------------|-------------|------|-------------|------------------------------------------------------|
| id                | UUID        | NO   | `uuid4()`   | PK                                                   |
| organization_id   | UUID        | NO   | —           | Multi-tenancy boundary                               |
| agent_id          | UUID        | YES  | —           | FK → `agents.id` ON DELETE SET NULL                  |
| channel_id        | UUID        | YES  | —           | FK → `channels.id` ON DELETE SET NULL                |
| from_number       | VARCHAR(20) | YES  | —           | E.164                                                |
| to_number         | VARCHAR(20) | YES  | —           | E.164                                                |
| status            | VARCHAR(30) | NO   | —           | `completed` / `failed` / `dropped` / `no_answer`     |
| started_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |
| ended_at          | TIMESTAMPTZ | YES  | —           | NULL while call is live                              |
| duration_seconds  | INT         | YES  | —           | Computed at end                                      |
| transcript        | JSONB       | YES  | —           | `[{role, text, timestamp}]` or similar               |
| metrics           | JSONB       | YES  | —           | `{tokens, latencies, ...}`                           |
| created_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |
| updated_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |

**Indexes**:
- ⚠ Likely missing: `ix_calls_org_started_at` — needed for the dashboard's `started_at` filters too.

**Audio storage**: separate `Upload` row with `purpose='call_audio'` pointing to R2 (`uploads/{org_id}/calls/{call_id}.mp3`).

## 7. API design

Router prefix (when re-enabled): `/api/v1/call-log` (singular — matches frontend `axiosInstance.post('/call-log/list')`). Currently disabled in `main.py:19`.

| Method | Path                                | Purpose                                                  |
|--------|-------------------------------------|----------------------------------------------------------|
| GET    | `/call-log/filter-values`           | Unique values for filter dropdowns                       |
| POST   | `/call-log/list`                    | Paginated list with filters                              |
| GET    | `/call-log/{call_id}`               | Call detail with transcript + metrics                    |
| GET    | `/call-log/{call_id}/audio-url`     | Signed R2 URL for audio                                  |
| GET    | `/call-log/{call_id}/audio`         | Stream audio with range support                          |

### POST /call-log/list

```json
{
  "page_no": 1, "page_size": 20,
  "search": "+15551234567",
  "sort_by": "-started_at",
  "filter_by": {"agent_id": "uuid", "status": "completed"},
  "from_date": "2026-05-01",
  "to_date": "2026-05-27"
}
```

### Response

```json
{
  "items": [{
    "id": "uuid", "agent_id": "uuid", "channel_id": "uuid",
    "from_number": "+15551234567", "to_number": "+15559876543",
    "status": "completed",
    "started_at": "2026-05-27T10:00:00+00:00",
    "ended_at": "2026-05-27T10:03:45+00:00",
    "duration_seconds": 225,
    "agent_name": "Sales Bot"
  }],
  "total": 1, "page_no": 1, "page_size": 20
}
```

### GET /call-log/{call_id}

```json
{
  "id": "uuid", "agent_id": "uuid", "channel_id": "uuid",
  "from_number": "+15551234567", "to_number": "+15559876543",
  "status": "completed", "started_at": "...", "ended_at": "...",
  "duration_seconds": 225,
  "transcript": [
    {"role": "agent", "text": "Hi, this is Acme. How can I help?", "timestamp": "..."},
    {"role": "user", "text": "I want to book a meeting", "timestamp": "..."}
  ],
  "metrics": {"llm_tokens_in": 412, "llm_tokens_out": 78, "ttfb_ms": 320}
}
```

## 8. Backend implementation

- **Controller**: `core/api/v1/call_logs.py` — 5 routes.
- **EE Controller**: `ee/api/v1/call_logs.py` — mirrors and correctly passes `org_id`.
- **Service**: `core/services/call_log_service.py` — ⚠ imports non-existent `core.models.call_log.CallLog`. Will `ImportError` at startup if mounted.
- **Models**:
  - `core/models/call.py` — v2 `Call` model.
  - `core/models/upload.py` — v2 `Upload` (does NOT match service's expected `r2_object_key`/`call_log_id`/`file_size_bytes` fields).
- **Storage helpers**:
  - `core/utils/storage.py` — R2 presigned URL + ranged GET.
  - `core/services/r2_storage_service.py` — R2 wrapper.
- **Pipeline writer**: `core/services/agent_factory_service.py` lines 1280-1450 (verify).

## 9. Frontend implementation

- **Route**: `/call-history` — `frontend/src/app/(dashboard)/call-history/page.tsx`.
- **Components** (`frontend/src/components/call-history/`):
  - `CallHistory.tsx` — list view with `CustomTable`.
  - `CallDetailDrawer.tsx` — slide-in drawer with transcript + audio player + metrics.
  - `FilterSortModal.tsx`, `SortModal.tsx` — filter UX.
  - `TranscriptionModal.tsx` — full transcript view.
  - `MetricsModal.tsx`, `metrics/` — call metrics breakdown.
- **API service**: `frontend/src/services/callLogService.ts`.
- **Types**: `frontend/src/types/callLog.ts`.
- **State**: Jotai atoms in `frontend/src/atoms/CallLogAtom.tsx`.
- **Audio playback**: HTML5 `<audio>` element with `src={audioUrl}`. Range-request support is required for seeking.

## 10. Postman collection & examples

`postman_collection/call_logs.postman_collection.json`. ⚠ Samples use ISO strings for `from_date`/`to_date` but service may expect epoch ints; nested `pagination` wrapper but service returns flat.

### POST /api/v1/call-log/list

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"page_no":1,"page_size":20,"filter_by":{"status":"completed"}}' \
  "$BASE_URL/api/v1/call-log/list"
```

### GET /api/v1/call-log/{call_id}/audio-url

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/call-log/550e8400-.../audio-url"
```

```json
{"url": "https://r2.cloudflare/uploads/org/calls/550e8400....mp3?X-Amz-Expires=3600&..."}
```

### GET /api/v1/call-log/{call_id}/audio (range)

```bash
curl -H "Authorization: Bearer $TOKEN" -H "Range: bytes=0-1023" \
  "$BASE_URL/api/v1/call-log/550e8400-.../audio" --output partial.mp3
```

Returns `206 Partial Content` with bytes 0–1023.

## 11. Next steps

- [ ] ⚠ **Re-enable router** in `main.py:19`. First fix the service-layer ImportError and schema drift.
- [ ] ⚠ **Fix `call_log_service.py` imports**: replace `core.models.call_log.CallLog` with `core.models.call.Call`.
- [ ] ⚠ **Reconcile `Upload` field names**: service uses `r2_object_key`/`call_log_id`/`file_size_bytes`; v2 has `file_path` and no `call_log_id`. Either add a `call_id` FK on `uploads` (`purpose='call_audio'`) or rename service usage.
- [ ] ⚠ **Core controller should pass `org_id`** to the service (EE does).
- [ ] ⚠ **Add pagination clamping** (`page_size ≤ 100`, `page_no ≥ 1`).
- [ ] ⚠ **Add per-column operator allow-list** so `contains` can't be applied to int columns.
- [ ] ⚠ **Fix Postman samples** — epoch ints + flat response shape.
- [ ] ⚠ **Add an index** on `calls(organization_id, started_at)`.
- [ ] ⚠ **Add tests** under `tests/test_call_logs.py`.
- [ ] **Pipeline writer**: verify `agent_factory_service.py` actually writes call rows on end-of-call (per [[dashboard]] §3 the pipeline cut-over to `calls` may not be complete).
- [ ] **Add export endpoint** (`POST /call-log/export` → CSV/JSON) for offline analysis.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) `call_logs` router is **disabled in `main.py:19`** — endpoints return 404; (2) `call_log_service.py` imports non-existent `core.models.call_log.CallLog`; (3) Service expects `Upload` fields (`r2_object_key`, `call_log_id`, `file_size_bytes`) that don't exist on the v2 model; (4) Core controller doesn't pass `org_id` to service — multi-tenancy relies on context-var fallback; (5) No pagination clamping; (6) No per-column operator allow-list; (7) No automated tests; (8) Postman samples drifted (ISO strings vs epoch, nested pagination wrapper); (9) Pipeline write path's wiring to `calls` is verified incomplete per [[dashboard]] §3.
