# Feature Doc: Knowledge Base

Feature documentation for the Knowledge Base page. Used by
`/generate-tests knowledge-base` (or `--docs e2e/ux_flow_docs/knowledge-base.md`) to
ensure all user cases are covered.

The Knowledge Base lets agent owners upload documents (PDF, DOCX, TXT, CSV,
JSON, HTML) and associate them with an agent so the voice pipeline can answer
from those documents at call-time via RAG (retrieval-augmented generation).

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/knowledge-base`
- **Component (wrapper)**: `src/app/(dashboard)/knowledge-base/page.tsx`
- **Main component**: `src/components/knowledge-base/KnowledgeBasePage.tsx`
- **Sub-components**:
  - `src/components/knowledge-base/DocumentUpload.tsx` (Add Sources modal)
  - `src/components/knowledge-base/EditDocument.tsx` (rename + replace-file modal)
  - `src/components/knowledge-base/knowledgeBaseListConfig.ts` (faceted-list config, status polling)
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fknowledge-base` without `tone_access_token` cookie)

---

## User Stories

### US-1: Browse the document list

**As an** agent owner, **I want to** see a table of all documents in my org,
**so that** I know what knowledge my agents can draw on.

**Acceptance criteria**:

- [ ] Page header shows "Knowledge Base" (h1) + subtitle "Upload documents to enhance your AI agents with custom knowledge."
- [ ] Primary CTA "Add Sources" appears in the header
- [ ] Search bar placeholder: "Search documents… (e.g. name:resort, status:ready)"
- [ ] Table columns: checkbox (select all), Name / Type, Size, Status, Last updated, action icons
- [ ] Status badge renders as "Active" (green), "Processing" (amber, pulsing dot), or "Failed" (red)
- [ ] Empty state with no documents: icon + "No documents yet" + subtitle + "Add Sources" button
- [ ] Empty state with active filters: different text encouraging the user to clear filters

### US-2: Upload one or more documents

**As an** agent owner, **I want to** drop files into an upload modal and pick
the agent they belong to, **so that** I can attach knowledge in one step.

**Acceptance criteria**:

- [ ] "Add Sources" opens the `DocumentUpload` modal
- [ ] Required Agent select (disabled if the org has no agents) lists agents from the agent atom
- [ ] Drag-and-drop zone reads: "Drag & drop or **browse files**"; clicking opens the file picker
- [ ] Supported types: PDF, DOCX, TXT, CSV, JSON, HTML (100 MB per file max)
- [ ] Unsupported types or files >100 MB show a toast error and are not added to the queue
- [ ] Files with the same name + size as an already-queued file are deduplicated silently
- [ ] Selected files show as rows with icon, name, size, remove button (X)
- [ ] Upload progress shows "Uploading N of M" + percentage bar
- [ ] Primary CTA reads "Upload N files" / "Upload document" and is disabled until both Agent and at least one file are selected
- [ ] On success: modal closes, table refetches; failed uploads (if any) surface a partial-success toast

### US-3: Open document details

**As an** agent owner, **I want to** click a row to see file metadata and
status, **so that** I can verify processing or diagnose failures.

**Acceptance criteria**:

- [ ] Clicking any row opens the "Document details" modal
- [ ] Modal shows: file icon + name + file-type badge + status badge, associated agent name, file size, uploaded date, last-updated date
- [ ] If status === "failed": an AlertTriangle alert with the title "Processing failed", the `meta_data.error` message, and a "Retry processing" button
- [ ] Footer buttons: Delete (danger), Edit (primary), View file (only if a URL exists, opens in a new tab)

### US-4: Rename a document or replace its file

**As an** agent owner, **I want to** rename a document or swap the underlying
file, **so that** I can keep references stable while updating content.

**Acceptance criteria**:

- [ ] "Edit" from the detail modal opens the `EditDocument` modal
- [ ] File name input is required, pre-filled with the current file_name
- [ ] Optional drop zone: "Drop or **browse** to replace"; renders the picked file or current file preview with a remove (X) action
- [ ] "Save changes" is disabled until the user changes something (dirty check)
- [ ] Submitting without a new file calls `PATCH /knowledge-base/{id}` with the new name
- [ ] Submitting with a new file calls `PATCH /knowledge-base/{id}/file` (multipart)
- [ ] On success: modals refresh, table re-renders, success toast shown

### US-5: Retry a failed document

**As an** agent owner, **I want to** click "Retry" on a failed document,
**so that** I don't have to re-upload to fix transient errors.

**Acceptance criteria**:

- [ ] Inline retry icon on a failed row and "Retry processing" in the detail modal both call `POST /knowledge-base/{id}/reprocess`
- [ ] Row badge flips to "Processing" (amber, pulsing) immediately after retry
- [ ] Status polling (every 4s while any row is processing) flips the badge to "Active" or "Failed" once the backend responds

### US-6: Delete one or many documents

**As an** agent owner, **I want to** delete one document or bulk-delete
several, **so that** I can clean up the knowledge base.

**Acceptance criteria**:

- [ ] Row action icon and detail-modal "Delete" call `DELETE /knowledge-base/{id}`
- [ ] Selecting checkboxes reveals a floating bottom bar showing the selection count + "Clear" + "Delete"
- [ ] "Delete" in the floating bar fans out via `Promise.allSettled`; failed IDs remain selected and surface a partial-success toast
- [ ] Successful deletes are removed from the table optimistically/refetched

---

## Input Specifications

### Document Upload modal (`DocumentUpload.tsx`)

| Field      | Type            | Required | Validation Rules                                                                                       | Exact Error Message                                                                                          |
| ---------- | --------------- | -------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Agent      | Select          | yes      | Must be a non-empty UUID; dropdown disabled if `agentList` is empty                                    | Submit button stays disabled — no toast                                                                       |
| Documents  | File[] (multi)  | yes (≥1) | Extension ∈ `pdf, txt, csv, html, json, docx`; size ≤ `100 * 1024 * 1024` bytes (100 MB)                | Unsupported: `Unsupported: <file.name>` / `Supported: pdf, txt, csv, html, json, docx`                       |
|            |                 |          |                                                                                                        | Oversize: `Too large: <file.name>` / `Maximum file size is 100 MB`                                            |
|            |                 |          | Duplicate (same `name` + `size` as already in queue) → silently dropped, no toast                       | (no toast)                                                                                                    |

ACCEPTED_TYPES (HTML `accept` attribute): `application/pdf, text/plain, text/csv, text/html, application/json, application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

### Edit Document modal (`EditDocument.tsx`)

| Field        | Type   | Required | Validation Rules                                                          | Exact Error Message                                                  |
| ------------ | ------ | -------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| File name    | text   | yes      | `fileName.trim().length > 0`; differs from original OR a new file picked | On save with empty name (defensive): toast title `Name required`, description `Please enter a file name before saving.` |
| Replace file | File   | no       | Same extension + 100 MB rule as upload (validateFile)                     | Same messages as upload modal                                         |

Save button (`Save changes`) is disabled when `canSave === false` (no trimmed name OR no change). Backend `file_name too long` returns server message `file_name too long (max 512)` rendered via `handleApiError`.

---

## Expected Toast Messages

Sonner toast titles + descriptions from source (`src/utils/toast.tsx`, `DocumentUpload.tsx`, `EditDocument.tsx`, `KnowledgeBasePage.tsx`, `helpers.ts`). Assert via `page.locator('[data-sonner-toast]').first()`.

| Trigger                                            | Toast title                                      | Toast description                                                         | Variant |
| -------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------- | ------- |
| Upload — 1 file succeeds                            | `Document uploaded`                              | `Your documents are now part of the knowledge base.`                      | success |
| Upload — N (>1) files all succeed                   | `N documents uploaded`                           | `Your documents are now part of the knowledge base.`                      | success |
| Upload — partial success                            | `K of N uploaded`                                | `M failed — retry the remaining files.`                                   | error   |
| Upload — all fail                                   | (server `detail` string OR `Something went wrong. Please try again.`) | (none — single-arg)                                  | error   |
| File rejected — unsupported extension               | `Unsupported: <file.name>`                       | `Supported: pdf, txt, csv, html, json, docx`                              | error   |
| File rejected — oversize (>100 MB)                  | `Too large: <file.name>`                         | `Maximum file size is 100 MB`                                             | error   |
| Rename only                                         | `Document renamed`                               | (none)                                                                    | success |
| Replace file (no rename)                            | `File replaced`                                  | `Changes saved successfully.`                                             | success |
| Replace file + rename                               | `File replaced & renamed`                        | `Changes saved successfully.`                                             | success |
| Edit — defensive empty name                         | `Name required`                                  | `Please enter a file name before saving.`                                 | error   |
| Reprocess success                                   | `Retrying`                                       | `Document processing has been restarted.`                                 | success |
| Single delete success                               | `Document deleted`                               | (none)                                                                    | success |
| Bulk delete — 1 succeeds                            | `Document deleted`                               | (none)                                                                    | success |
| Bulk delete — N succeed                             | `N documents deleted`                            | (none)                                                                    | success |
| Bulk delete — all fail                              | `Bulk delete failed`                             | `No documents were deleted.`                                              | error   |
| Bulk delete — partial fail                          | `Partial delete`                                 | `K of N deleted. M failed — refresh and try again.`                       | error   |
| Any unhandled API error                             | (server `detail` string OR `Something went wrong. Please try again.`) | (none)                                  | error   |

---

## UI Elements

| Element                       | Type        | Content / Label                                                | Behavior                                                       |
| ----------------------------- | ----------- | -------------------------------------------------------------- | -------------------------------------------------------------- |
| Page heading                  | h1          | "Knowledge Base"                                               | Static                                                         |
| Page subtitle                 | body1       | "Upload documents to enhance your AI agents…"                  | Static                                                         |
| Add Sources button            | Button      | "Add Sources"                                                  | Opens `DocumentUpload` modal                                   |
| Search bar                    | TokenSearch | "Search documents… (e.g. name:resort, status:ready)"           | Token-based, posts filters to `/knowledge-base/list`           |
| Filters drawer button         | Button      | SlidersHorizontal icon + filter count badge                    | Opens drawer with status facets                                |
| Table column: select-all      | Checkbox    | —                                                              | Toggles all rows on the current page                           |
| Table column: Name / Type     | Cell        | file icon + truncated name + type badge (PDF/DOCX/…)           | Click opens detail modal                                       |
| Table column: Size            | Cell        | formatted bytes (KB/MB)                                        | —                                                              |
| Table column: Status          | Badge       | Active / Processing (pulsing dot) / Failed                     | Polls every 4s while any row is "Processing"                   |
| Table column: Last updated    | Cell        | locale date                                                    | —                                                              |
| Table action icons            | Icons       | edit / retry (failed only) / delete                            | —                                                              |
| Floating selection bar        | Bar         | "N selected" + "Clear" + "Delete"                              | Appears when at least one row is selected                      |
| Empty state (no docs)         | Card        | "No documents yet" + "Add Sources" button                      | Shown when total === 0                                         |
| Empty state (no matches)      | Card        | "No documents match your filters"                              | Shown when total === 0 but filters are active                  |
| Upload — Agent select         | SelectInput | label "Agent"                                                  | Required; disabled if no agents                                |
| Upload — drop zone            | Drop area   | "Drag & drop or browse files" (PDF / DOCX / TXT / CSV / JSON / HTML, 100 MB max) | Multi-file, deduped by name+size                |
| Upload — file row             | Row         | icon + name + size + X (remove)                                | Removes from the queue                                         |
| Upload — progress             | Progress    | "Uploading N of M" + percentage                                | Hidden until submit pressed                                    |
| Upload — primary CTA          | Button      | "Upload N files" / "Upload document"                           | Disabled until agent + ≥1 file picked                          |
| Edit — file name input        | TextInput   | placeholder "document.pdf"                                     | Required                                                       |
| Edit — replace drop zone      | Drop area   | "Drop or browse to replace"                                    | Optional                                                       |
| Edit — Save changes button    | Button      | "Save changes"                                                 | Disabled until dirty                                           |
| Detail modal — Retry button   | Button      | "Retry processing"                                             | Only on failed documents                                       |
| Detail modal — View file      | Link        | "View file"                                                    | Opens `meta_data.url` in a new tab when present                |

---

## Navigation

| Trigger                              | Destination                                       | Condition                                  |
| ------------------------------------ | ------------------------------------------------- | ------------------------------------------ |
| Click "Add Sources"                  | `DocumentUpload` modal opens                      | Always                                     |
| Click a row                          | Detail modal opens                                | Always                                     |
| Click "Edit" in detail modal         | `EditDocument` modal opens                        | Always                                     |
| Click "Delete" in detail modal       | Confirm dialog → `DELETE /knowledge-base/{id}`    | Always                                     |
| Click retry icon / "Retry processing"| `POST /knowledge-base/{id}/reprocess`             | Status === "failed"                        |
| Click "View file"                    | Opens `meta_data.url` in a new tab                | Document has a URL                         |
| Selection + "Delete" in floating bar | Bulk DELETE via Promise.allSettled                | At least one row selected                  |
| No auth cookie                       | `/auth/login?redirect=%2Fknowledge-base`          | `src/middleware.ts` redirect               |

---

## API Contracts

Prefix: `/api/v1`. Verified against the Postman collection (`Knowledge Base` folder) and `src/lib/api/knowledge-base.ts`.

| Endpoint                          | Method | Request                                                                              | Success                                              | Error                |
| --------------------------------- | ------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------- | -------------------- |
| `/knowledge-base/list`            | POST   | `{ page, page_size, search?, sort_by?, agent_id?, status? }`                         | `200 { items: KBDoc[], total, page, page_size }`     | `{ detail: "..." }`  |
| `/knowledge-base/facets`          | POST   | `{ filters: Array<{field, operator, value}> }`                                       | `200 { status: { ready, processing, failed } }`      | `{ detail: "..." }`  |
| `/knowledge-base/filter-values`   | GET    | `?column_name=status`                                                                | `200 { values: string[] }`                           | `{ detail: "..." }`  |
| `/knowledge-base`                 | POST   | multipart: `file` + `agent_id` (text)                                                | `201 KBDoc` (status starts `processing`)             | `{ detail: "..." }`  |
| `/knowledge-base/{id}`            | PATCH  | `{ file_name: string }`                                                              | `200 KBDoc`                                          | `{ detail: "..." }`  |
| `/knowledge-base/{id}/file`       | PATCH  | multipart: `file` + optional `file_name` (text)                                      | `200 KBDoc` (status reset to `processing`)           | `{ detail: "..." }`  |
| `/knowledge-base/{id}/reprocess`  | POST   | —                                                                                    | `202 KBDoc` (status `processing`, `meta_data.error` cleared) | `{ detail: "..." }` |
| `/knowledge-base/{id}`            | DELETE | —                                                                                    | `200 { ok: true }`                                   | `{ detail: "..." }`  |

### Example — `POST /knowledge-base/list`

Request body:
```json
{"page": 1, "page_size": 20, "search": "policy", "sort_by": "-created_at", "agent_id": "a-1", "status": "ready"}
```
Success (200):
```json
{
  "items": [
    {"id": "8a3f1c12-2b9e-4a51-9b3a-5fe2dc4d7a01", "file_name": "refund_policy.pdf", "file_type": "application/pdf", "size_bytes": 245678, "status": "ready", "agent_id": "a-1", "url": "https://r2.example.com/...", "meta_data": {}, "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:02:00+00:00"}
  ],
  "total": 1, "page": 1, "page_size": 20
}
```
Validation error (422):
```json
{"detail":[{"loc":["body"],"msg":"value is not a valid dict","type":"type_error.dict"}]}
```

### Example — `POST /knowledge-base` (multipart upload)

Form fields: `file` (binary), `agent_id` (text UUID).

Success (201):
```json
{
  "id": "8a3f1c12-2b9e-4a51-9b3a-5fe2dc4d7a01",
  "file_name": "company-handbook.pdf",
  "file_type": "application/pdf",
  "size_bytes": 482133,
  "purpose": "kb_document",
  "status": "processing",
  "meta_data": {},
  "created_at": "2026-06-17T10:14:32.118500+00:00",
  "updated_at": "2026-06-17T10:14:32.118500+00:00",
  "url": "https://r2.example.com/knowledge-base/org/.../company-handbook.pdf?X-Amz-Signature=..."
}
```
Failed status example (201, processing pipeline rejected):
```json
{"id":"8a3f1c12-...","file_name":"broken.pdf","file_type":"application/pdf","size_bytes":1024,"status":"failed","meta_data":{"error":"No OpenAI API key configured for embedding"},"created_at":"2026-06-17T10:14:32+00:00","updated_at":"2026-06-17T10:14:33+00:00","url":"https://r2.example.com/..."}
```
Validation error (422 missing file):
```json
{"detail":[{"loc":["body","file"],"msg":"field required","type":"value_error.missing"}]}
```
Common errors: `400 {"detail":"Invalid agent_id"}` · `400 {"detail":"Empty file"}` · `401 {"detail":"Invalid token"}` · `404 {"detail":"Agent not found"}` · `409 {"detail":"Agent has no published configuration yet. Save and publish the agent before uploading knowledge base documents."}`.

### Example — `PATCH /knowledge-base/{id}` (rename)

Request body: `{"file_name":"refund_policy_2026.pdf"}`. Success (200):
```json
{"id":"8a3f1c12-...","file_name":"refund_policy_2026.pdf","file_type":"application/pdf","size_bytes":245678,"status":"ready","url":"https://r2.example.com/...","updated_at":"2026-05-27T10:10:00+00:00"}
```
Errors: `400 {"detail":"Invalid upload_id"}` · `400 {"detail":"file_name is required"}` · `400 {"detail":"file_name too long (max 512)"}` · `404 {"detail":"Upload not found"}`.

### Example — `PATCH /knowledge-base/{id}/file` (replace)

Multipart: `file` (binary) + optional `file_name`. Success (200):
```json
{"id":"8a3f1c12-...","file_name":"company-handbook-v2.pdf","file_type":"application/pdf","size_bytes":612874,"status":"processing","meta_data":{},"updated_at":"2026-06-17T11:02:11+00:00","url":"https://r2.example.com/..."}
```
Errors mirror upload + `404 {"detail":"Upload not found"}` and `422 {"detail":[{"loc":["body","file"],"msg":"field required","type":"value_error.missing"}]}`.

### Example — `POST /knowledge-base/{id}/reprocess`

Success (202):
```json
{"id":"8a3f1c12-...","file_name":"company-handbook.pdf","status":"processing","meta_data":{},"updated_at":"2026-06-17T11:20:09+00:00"}
```
Errors: `400 {"detail":"Upload has no stored file to reprocess"}` · `404 {"detail":"Upload not found"}` · `404 {"detail":"Document not found"}`.

### Example — `DELETE /knowledge-base/{id}`

Success (200): `{"ok": true}`. Errors: `400 {"detail":"Invalid upload_id"}` · `404 {"detail":"Upload not found"}` · `401 {"detail":"Invalid token"}`.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.

---

### TC-HAPPY-001: List loads with documents (PS-1 / WF-1)

**Preconditions**:
- Logged in; `POST /knowledge-base/list` returns 2 items including one `ready` and one `processing`.

**Action**:
1. Authenticate via `loginViaUI(page)`
2. Navigate to `/knowledge-base`

**Observation 1 — Headings + toolbar render**:
1. h1 reads `Knowledge Base`
2. Subtitle contains `Upload documents to enhance your AI agents`
3. `Add Sources` button is visible
4. Search bar placeholder reads `Search documents… (e.g. name:resort, status:ready)`

**Observation 2 — Table renders rows**:
1. Two rows are visible
2. One status badge reads `Active`; one reads `Processing`
3. `Last updated` column shows a formatted date

**API mock**: `POST /knowledge-base/list` → 200 PS-1 body.

---

### TC-HAPPY-002: Sort by Name / Type fires list with sort payload (WF-1 step 3)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Click the `Name / Type` column header

**Observation 1 — Refetch with sort**:
1. `POST /knowledge-base/list` fires
2. Request body includes `sort_by: "file_name", sort_order: "asc"`

---

### TC-HAPPY-003: Change page size to 50 (WF-1 step 4)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Change page size to 50

**Observation 1 — Refetch with page size**:
1. `POST /knowledge-base/list` re-fires
2. Request body has `page_size: 50, page: 1`

---

### TC-HAPPY-004: Empty list shows the no-docs empty state (PS-2 / KB-028)

**Preconditions**: `POST /knowledge-base/list` returns `{"items":[], "total":0}`.

**Action**:
1. Navigate to `/knowledge-base`

**Observation 1 — No-docs empty state**:
1. Heading reads `No documents yet`
2. A descriptive subtitle is visible
3. `Add Sources` CTA is visible

---

### TC-HAPPY-005: Upload a single document (WF-2 / PS-3)

**Preconditions**: Authenticated; agents atom has ≥1 agent.

**Action**:
1. Click `Add Sources`
2. Pick an agent from the `Agent` dropdown
3. Drop `policy.pdf` (2 MB) on the drop zone
4. Click `Upload document`

**Observation 1 — Modal initial state**:
1. Modal title reads `Add sources`
2. Primary button text equals `Upload document`
3. Primary button is `disabled` until both agent + file are selected

**Observation 2 — Queue row appears after drop**:
1. A row with filename `policy.pdf`, size `2.0 MB`, and an X remove button is visible
2. Primary button enables

**Observation 3 — Upload request fires**:
1. Exactly one multipart `POST /knowledge-base` request fires
2. Form fields include `agent_id` and `file`

**Observation 4 — Success surface**:
1. Modal closes
2. `POST /knowledge-base/list` re-fires (table refetch)
3. Toast title equals `Document uploaded`
4. Toast description equals `Your documents are now part of the knowledge base.`

**API mock**: `POST /knowledge-base` → 201 PS-3 body.

---

### TC-HAPPY-006: Upload multiple documents with progress (WF-3 / PS-4)

**Preconditions**: TC-HAPPY-005's preconditions; 3 valid files queued.

**Action**:
1. Open `Add Sources`, pick agent, drop 3 valid files
2. Click `Upload 3 files`

**Observation 1 — Queue and CTA reflect count**:
1. Primary button text equals `Upload 3 files`
2. Queue shows 3 rows

**Observation 2 — Progress UI advances**:
1. Progress UI shows `Uploading 1 of 3`, then `2 of 3`, then `3 of 3`
2. The percentage bar advances

**Observation 3 — Sequential requests fire**:
1. Three sequential `POST /knowledge-base` calls fire

**Observation 4 — Final success surface**:
1. Modal closes
2. Toast title equals `3 documents uploaded`

---

### TC-HAPPY-007: Open document details (WF-4)

**Preconditions**: TC-HAPPY-001; an `Active` row visible.

**Action**:
1. Click the `Active`-status row

**Observation 1 — Modal opens with metadata**:
1. `Document details` modal opens
2. File name, type badge (e.g. PDF), and status badge `Active` are visible
3. Rows show Agent, File size, Uploaded, Last updated

**Observation 2 — Footer buttons render**:
1. `Delete` button on the left
2. `Edit` button + `View file` button on the right
3. `View file` is hidden when `url` is null

---

### TC-HAPPY-008: View file opens URL in a new tab (PS-10 / KB-039 / KB-055)

**Preconditions**: TC-HAPPY-007 modal open; document has a `meta_data.url`.

**Action**:
1. Click `View file`

**Observation 1 — New tab opens with the URL**:
1. `window.open` is invoked with the URL and target `_blank`
2. A new tab opens at the document URL
3. The original tab remains on `/knowledge-base`

---

### TC-HAPPY-009: Edit — rename only (WF-5 / PS-5)

**Preconditions**: TC-HAPPY-007 modal open.

**Action**:
1. Click `Edit`
2. Clear the name and type `renamed.pdf`
3. Click `Save changes`

**Observation 1 — Modal preloaded**:
1. The `EditDocument` modal opens
2. File name input is pre-filled with the original `file_name`

**Observation 2 — Save changes enables**:
1. The Save button becomes enabled after the user changes the name

**Observation 3 — Rename request**:
1. Exactly one `PATCH /knowledge-base/{id}` fires
2. Request body equals `{"file_name":"renamed.pdf"}`

**Observation 4 — Success surface**:
1. Toast title equals `Document renamed`
2. Table refetches

**API mock**: `PATCH /knowledge-base/{id}` → 200.

---

### TC-HAPPY-010: Edit — replace file with rename (WF-6 / PS-6)

**Preconditions**: Edit modal open.

**Action**:
1. Drop `policy_v2.pdf` on the replace drop zone
2. Click `Save changes`

**Observation 1 — Drop zone collapses to preview**:
1. The drop zone is replaced by a single-file preview row showing `policy_v2.pdf`
2. Row indicates `replaces current file`
3. If the user had not edited the name field, the name auto-syncs to `policy_v2.pdf`

**Observation 2 — Multipart PATCH request**:
1. `PATCH /knowledge-base/{id}/file` fires
2. Multipart body includes `file` + optional `file_name`

**Observation 3 — Toast title depends on whether name changed**:
1. If name also changed: toast title `File replaced & renamed`
2. Otherwise: toast title `File replaced`
3. Description equals `Changes saved successfully.`

**API mock**: `PATCH /knowledge-base/{id}/file` → 200 PS-6 body.

---

### TC-HAPPY-011: Retry a failed document — inline icon (WF-7 / PS-7 / KB-043)

**Preconditions**: A row with `Failed` status.

**Action**:
1. Click the inline retry icon on the failed row

**Observation 1 — Reprocess request fires**:
1. Exactly one `POST /knowledge-base/{id}/reprocess` request is recorded

**Observation 2 — Toast**:
1. Toast title equals `Retrying`
2. Toast description equals `Document processing has been restarted.`

**Observation 3 — Row badge flips**:
1. Row badge becomes `Processing` immediately
2. Next status poll within 4 s reflects the latest backend state

**API mock**: `POST /knowledge-base/{id}/reprocess` → 202 PS-7 body.

---

### TC-HAPPY-012: Retry from detail modal triggers reprocess (KB-044)

**Preconditions**: Detail modal open for a `Failed` document.

**Action**:
1. Click `Retry processing` in the detail modal

**Observation 1 — AlertTriangle alert renders meta_data.error**:
1. The detail modal shows `Processing failed` title with the `meta_data.error` text

**Observation 2 — Reprocess request fires**:
1. `POST /knowledge-base/{id}/reprocess` fires

**Observation 3 — Toast + badge flip**:
1. Toast title `Retrying` appears
2. Badge becomes `Processing`

---

### TC-HAPPY-013: Single-row delete (WF-8 / PS-8)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Click the trash icon on a row
2. Click `Delete` in the confirm modal

**Observation 1 — Confirm modal copy**:
1. Title reads `Delete document`
2. Description reads `Are you sure you want to delete "<file_name>"? This action cannot be undone.`

**Observation 2 — Delete request**:
1. Exactly one `DELETE /knowledge-base/{id}` request fires

**Observation 3 — Success surface**:
1. Toast title equals `Document deleted`
2. The row disappears

**API mock**: `DELETE /knowledge-base/{id}` → 200 `{"ok": true}`.

---

### TC-HAPPY-014: Bulk delete (WF-9 / PS-9)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Check 3 rows
2. Click `Delete` in the floating bar
3. Click `Delete` in the confirm modal

**Observation 1 — Floating bar appears**:
1. Floating bar reads `3 documents selected`
2. `Clear` and `Delete` buttons are present

**Observation 2 — Confirm copy**:
1. Modal title reads `Delete documents`
2. Description reads `Delete 3 selected documents? This action cannot be undone.`

**Observation 3 — Parallel DELETE requests**:
1. 3 parallel `DELETE /knowledge-base/{id}` requests fire via `Promise.allSettled`

**Observation 4 — Success surface**:
1. Toast title equals `3 documents deleted`
2. Selection is cleared

---

### TC-NAV-001: Unauthenticated visit redirects to login (KB-001 / FS-20)

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/knowledge-base`

**Observation 1 — Middleware redirect**:
1. URL becomes `/auth/login?redirect=%2Fknowledge-base`

---

### TC-NAV-002: Expired token redirects to login (KB-002)

**Preconditions**: Expired `tone_access_token` cookie.

**Action**:
1. Visit `/knowledge-base`

**Observation 1 — Redirect + cleanup**:
1. URL becomes `/auth/login?redirect=%2Fknowledge-base`
2. Expired cookie is cleared

---

### TC-NAV-003: Member role upload behavior follows org policy (KB-003)

**Preconditions**: Logged-in member (non-admin/owner).

**Action**:
1. Open `Add Sources` and attempt an upload

**Observation 1 — Upload allowed or 403 toast**:
1. Either the upload succeeds (org policy allows members)
2. OR backend returns 403 with toast `Admin or Owner role required`

---

### TC-NAV-004: Org switch scopes the document list correctly (KB-004)

**Preconditions**: User from another org opens a stale link.

**Action**:
1. Visit `/knowledge-base`

**Observation 1 — List scoped to new org**:
1. `POST /knowledge-base/list` returns rows scoped to the new org

**Observation 2 — Stale doc ids 404**:
1. Edits or deletes on stale doc ids return 404

---

### TC-NAV-005: Browser back closes detail modal without leaving page (KB-056)

**Preconditions**: Detail modal open.

**Action**:
1. Press browser Back

**Observation 1 — Modal closes**:
1. Detail modal closes
2. URL is unchanged

**Observation 2 — List state preserved**:
1. The visible list rows and filters remain intact

---

### TC-NAV-006: Reload preserves the knowledge base list (KB-057)

**Preconditions**: Authenticated; on `/knowledge-base`.

**Action**:
1. Reload the page

**Observation 1 — List intact after reload**:
1. URL stays `/knowledge-base`
2. List rows render after reload
3. No auth redirect occurs

---

### TC-NAV-007: Agent link in detail navigates to the agent page (KB-058)

**Preconditions**: Detail modal open; document linked to an agent.

**Action**:
1. Click the linked agent name in the detail modal

**Observation 1 — Navigation**:
1. URL becomes `/agents/edit/<type>/<id>/overview`

---

### TC-ERROR-001: Upload blocked when no agent selected (FS-1)

**Action**:
1. Open `Add Sources`
2. Drop a file WITHOUT picking an agent

**Observation 1 — CTA stays disabled**:
1. `Upload document` button has `disabled` attribute
2. Zero `POST /knowledge-base` requests fire

---

### TC-ERROR-002: Oversize file (>100 MB) rejected at queue time (FS-2 / KB-021)

**Action**:
1. Drop a file with `size > 104857600` bytes

**Observation 1 — Error toast**:
1. Toast title equals `Too large: <name>`
2. Toast description equals `Maximum file size is 100 MB`

**Observation 2 — Not queued, no request**:
1. File is NOT added to the queue
2. Zero `POST /knowledge-base` requests fire

---

### TC-ERROR-003: Unsupported MIME / extension (FS-3 / KB-020)

**Action**:
1. Drop `evil.exe`

**Observation 1 — Error toast**:
1. Toast title equals `Unsupported: evil.exe`
2. Toast description equals `Supported: pdf, txt, csv, html, json, docx`

**Observation 2 — Not queued, no request**:
1. Queue is unchanged
2. Zero `POST /knowledge-base` requests fire

---

### TC-ERROR-004: Duplicate file in queue is deduped silently (FS-4 / KB-024)

**Action**:
1. Drop `a.pdf`
2. Drop the same `a.pdf` (same name + size) again

**Observation 1 — Queue length unchanged**:
1. Only 1 row remains in the queue

**Observation 2 — No toast**:
1. Zero toasts appear

---

### TC-ERROR-005: Upload server error (500) keeps modal open with queue (FS-5 / KB-010)

**Action**:
1. Single-file upload submit; backend returns 500

**Observation 1 — Modal stays open**:
1. Modal is still in the DOM
2. The failed file remains in the queue

**Observation 2 — Toast from handleApiError**:
1. Toast title equals `Something went wrong. Please try again.` OR the server `detail` string

**API mock**: `POST /knowledge-base` → 500.

---

### TC-ERROR-006: Upload 409 — agent has no published config (FS-6 / KB-009)

**Action**:
1. Submit a single-file upload

**Observation 1 — Backend 409 toast**:
1. Toast title equals `Agent has no published configuration yet. Save and publish the agent before uploading knowledge base documents.`

**Observation 2 — Modal preserved**:
1. Modal stays open
2. Failed file remains in queue

**API mock**: `POST /knowledge-base` → 409.

---

### TC-ERROR-007: Upload 422 missing file fallback (FS-7)

**Action**:
1. Submit upload

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.` (because `detail` is an array)

**Observation 2 — File remains in queue**:
1. File is still queued for retry

**API mock**: `POST /knowledge-base` → 422 with array `detail`.

---

### TC-ERROR-008: Upload 401 unauthorized (FS-8 / KB-006)

**Action**:
1. Submit upload

**Observation 1 — Error toast**:
1. Toast title equals `Invalid token`

**Observation 2 — Modal preserved**:
1. Modal stays open
2. Queue is preserved

**API mock**: `POST /knowledge-base` → 401.

---

### TC-ERROR-009: Upload partial success (FS-9)

**Action**:
1. Submit 3-file upload; 2 succeed (201) and 1 returns 500

**Observation 1 — Failed file remains queued**:
1. Only the failed file remains in the queue (succeeded files are removed)

**Observation 2 — Partial-success toast**:
1. Toast title equals `2 of 3 uploaded`
2. Toast description equals `1 failed — retry the remaining files.`

**Observation 3 — Modal + agent select preserved**:
1. Modal stays open
2. Agent select is NOT cleared

---

### TC-ERROR-010: Rename — file_name too long (FS-10 / KB-019)

**Action**:
1. Submit rename with a > 512-char name

**Observation 1 — Backend 400 toast**:
1. Toast title equals `file_name too long (max 512)`

**Observation 2 — Modal preserved**:
1. Modal stays open
2. `Save changes` re-enables

**API mock**: `PATCH /knowledge-base/{id}` → 400.

---

### TC-ERROR-011: Rename — upload not found (404) (FS-11 / KB-008)

**Action**:
1. Submit rename for a missing doc

**Observation 1 — Error toast**:
1. Toast title equals `Upload not found`

**API mock**: `PATCH /knowledge-base/{id}` → 404.

---

### TC-ERROR-012: Replace file — empty file (400) (FS-12 / KB-022)

**Action**:
1. Submit edit with an empty file

**Observation 1 — Error toast**:
1. Toast title equals `Empty file`

**Observation 2 — Modal preserved**:
1. Modal stays open
2. New file still listed

**API mock**: `PATCH /knowledge-base/{id}/file` → 400.

---

### TC-ERROR-013: Reprocess — no stored file (400) (FS-13)

**Action**:
1. Click retry on a failed row

**Observation 1 — Error toast**:
1. Toast title equals `Upload has no stored file to reprocess`

**Observation 2 — Status unchanged**:
1. Row status remains `Failed`

**API mock**: `POST /knowledge-base/{id}/reprocess` → 400.

---

### TC-ERROR-014: Reprocess — document not found (404) (FS-14)

**Action**:
1. Click retry on a deleted doc

**Observation 1 — Error toast**:
1. Toast title equals `Document not found`

**API mock**: `POST /knowledge-base/{id}/reprocess` → 404.

---

### TC-ERROR-015: Single delete failure (500) (FS-15)

**Action**:
1. Confirm a single-row delete; backend returns 500

**Observation 1 — Confirm modal closes**:
1. Modal is no longer in the DOM

**Observation 2 — Row remains + error toast**:
1. Row is still visible
2. `handleApiError` toast appears

---

### TC-ERROR-016: Bulk delete — all fail (FS-16)

**Action**:
1. Trigger bulk delete with 3 selected; all 3 return 500

**Observation 1 — Error toast**:
1. Toast title equals `Bulk delete failed`
2. Toast description equals `No documents were deleted.`

**Observation 2 — Selection persists**:
1. Floating selection bar still shows all 3 selected

---

### TC-ERROR-017: Bulk delete — partial failure (FS-17 / KB-041)

**Action**:
1. Trigger bulk delete with 3 selected; 2 succeed and 1 fails

**Observation 1 — Partial-failure toast**:
1. Toast title equals `Partial delete`
2. Toast description equals `2 of 3 deleted. 1 failed — refresh and try again.`

**Observation 2 — Failed IDs remain selected**:
1. Floating selection bar shows `1 document selected` (only the failed ID)

---

### TC-ERROR-018: Unauthorized list (401) shows empty state, no infinite spinner (FS-18 / KB-005)

**Action**:
1. Navigate to `/knowledge-base`

**Observation 1 — Empty state**:
1. List shows empty state (no-matches OR no-docs depending on `hasActiveFilters`)
2. No infinite spinner

**API mock**: `POST /knowledge-base/list` → 401.

---

### TC-ERROR-019: Validation 422 on list does not crash (FS-19)

**Action**:
1. Navigate to `/knowledge-base`

**Observation 1 — Empty list, no crash**:
1. List state remains empty
2. Component does not throw on missing `items`

**API mock**: `POST /knowledge-base/list` → 422 with array `detail`.

---

### TC-ERROR-020: Delete 403 forbidden (KB-007)

**Action**:
1. Click delete on a row

**Observation 1 — Forbidden toast**:
1. Toast title surfaces backend `detail` (403)

**Observation 2 — Row remains**:
1. Row is still visible

**API mock**: `DELETE /knowledge-base/{id}` → 403.

---

### TC-ERROR-021: Delete a document already removed (404) (KB-008)

**Action**:
1. Click delete on a stale row

**Observation 1 — Error toast**:
1. Toast title equals `Upload not found`

**Observation 2 — Stale row removed on refetch**:
1. A subsequent refetch removes the row from the list

**API mock**: `DELETE /knowledge-base/{id}` → 404.

---

### TC-LOADING-001: Upload network failure preserves queue (KB-011)

**Action**:
1. Submit upload while offline

**Observation 1 — Toast and recovery**:
1. Toast title equals `Something went wrong. Please try again.`
2. Modal stays open
3. Failed file is still queued

**API mock**: `route.abort('failed')` for upload.

---

### TC-LOADING-002: Slow upload shows progress with disabled CTA (KB-012)

**Preconditions**: `POST /knowledge-base` delays > 3 s.

**Action**:
1. Submit a single-file upload

**Observation 1 — Progress + disabled CTA**:
1. Progress UI shows `Uploading 1 of 1` + percentage bar
2. Primary CTA has `disabled` attribute

---

### TC-LOADING-003: Slow list keeps skeleton without blocking Add Sources (KB-013)

**Preconditions**: `POST /knowledge-base/list` delays > 3 s.

**Action**:
1. Navigate to `/knowledge-base`

**Observation 1 — Skeleton + Add Sources enabled**:
1. Skeleton rows visible throughout
2. `Add Sources` button remains enabled

---

### TC-LOADING-004: Concurrent reprocess and poll converges on latest state (KB-014)

**Action**:
1. Trigger reprocess while a status poll is mid-flight

**Observation 1 — UI converges to latest backend state**:
1. UI does not flip between Processing and Failed
2. Latest poll wins

---

### TC-LOADING-005: Bulk delete partial network failure surfaces partial toast (KB-015)

**Action**:
1. Trigger bulk delete with 3 selected; one DELETE fails due to network

**Observation 1 — Partial-success toast**:
1. `Promise.allSettled` resolves
2. Toast title equals `Partial delete`

**Observation 2 — Failed IDs remain selected**:
1. Floating bar shows the failed ID still selected

---

### TC-EDGE-001: Whitespace-only file_name on edit (KB-016)

**Action**:
1. In the Edit modal, type only whitespace into the name field

**Observation 1 — Save disabled**:
1. `Save changes` button is `disabled` (`canSave === false`)

**Observation 2 — Defensive toast if reached**:
1. If submit somehow occurs, toast title equals `Name required`
2. Description equals `Please enter a file name before saving.`

---

### TC-EDGE-002: File name preserves or trims whitespace consistently (KB-017)

**Action**:
1. Type a file name with leading/trailing whitespace
2. Save

**Observation 1 — Round-trip consistency**:
1. Either backend trims OR sends as-is
2. Displayed value after refetch matches the sent value

---

### TC-EDGE-003: File name accepts unicode and html-ish characters without xss (KB-018)

**Action**:
1. Save a file name with special chars + emoji + unicode

**Observation 1 — Accepted**:
1. Save succeeds with the unicode/emoji name

**Observation 2 — Safe rendering**:
1. Table cell + detail modal render the name as plain text
2. `window.alert` was not invoked

---

### TC-EDGE-004: Drop empty file rejected before or during upload (KB-022)

**Action**:
1. Drop a 0-byte file
2. If queued, submit upload

**Observation 1 — Rejected**:
1. Either queue rejects before submit, OR backend returns 400 `Empty file`
2. Toast surfaces the appropriate detail

---

### TC-EDGE-005: Valid file uploaded round-trips into the list (KB-023)

**Action**:
1. Upload a valid file
2. Reload the list

**Observation 1 — Doc appears in list**:
1. After upload, a new row exists in the table

**Observation 2 — Click opens detail with same metadata**:
1. Clicking the row opens the detail modal with matching file name, size, agent

---

### TC-EDGE-006: Whitespace-only search treated as empty (KB-025)

**Action**:
1. Type only whitespace into the search bar

**Observation 1 — Sent as empty / default list**:
1. Request payload `search` is empty
2. List reverts to default

---

### TC-EDGE-007: Regex-special search characters do not crash list (KB-026)

**Action**:
1. Type regex-special characters into search

**Observation 1 — Sent verbatim**:
1. Backend treats as literal substring
2. No client crash

---

### TC-EDGE-008: Very long search does not crash the page (KB-027)

**Action**:
1. Paste a > 500-character search string

**Observation 1 — Page does not crash**:
1. Either accepted or backend truncates
2. No client crash

---

### TC-EDGE-009: Empty list under active filters renders no-results state (KB-029)

**Action**:
1. Apply filters that match no rows

**Observation 1 — No-results state**:
1. Heading reads `No documents match your filters`
2. A clear-filters CTA is present

---

### TC-EDGE-010: Pagination disables prev on first page (KB-030)

**Preconditions**: Multiple pages.

**Action**:
1. Observe pagination on page 1

**Observation 1 — Prev disabled, Next enabled**:
1. Prev button is `disabled`
2. Next button is enabled

---

### TC-EDGE-011: Pagination disables next on last page (KB-031)

**Preconditions**: Multiple pages.

**Action**:
1. Navigate to last page

**Observation 1 — Next disabled, Prev enabled**:
1. Next button is `disabled`
2. Prev button is enabled

---

### TC-EDGE-012: Sort by Name cycles asc and desc (KB-032)

**Action**:
1. Click `Name / Type` header twice

**Observation 1 — Two requests with toggled sort**:
1. First click sends `sort_by: 'file_name'` asc
2. Second click sends `sort_by: 'file_name'` desc

---

### TC-EDGE-013: Sort by Last updated orders descending (KB-033)

**Action**:
1. Click `Last updated` header

**Observation 1 — Sort payload**:
1. `POST /knowledge-base/list` fires with `sort_by: '-updated_at'`

---

### TC-EDGE-014: Removing a filter chip refetches without it (KB-034)

**Action**:
1. Click the X on a filter chip

**Observation 1 — Refetch without filter**:
1. Chip is removed
2. `POST /knowledge-base/list` re-fires without that filter

---

### TC-EDGE-015: Clear all filters resets filter state (KB-035)

**Action**:
1. Click `Clear all filters`

**Observation 1 — Reset**:
1. Every active filter is reset
2. List refetches

---

### TC-EDGE-016: Page size change resets to page 1 (KB-036)

**Action**:
1. Change page size

**Observation 1 — Re-fires with new size + page 1**:
1. `POST /knowledge-base/list` fires with the new `page_size` and `page: 1`

---

### TC-EDGE-017: Status badge reflects ingestion lifecycle (KB-038)

**Action**:
1. Upload a file
2. Wait through polling cycles

**Observation 1 — Lifecycle stages**:
1. Row status starts as `Processing` (amber pulsing dot)
2. After polling, the badge flips to `Active` or `Failed` once backend responds

---

### TC-EDGE-018: Bulk delete confirmation cancel preserves rows (KB-040)

**Action**:
1. Select 2 rows; click `Delete` in floating bar
2. Click Cancel in the confirm modal

**Observation 1 — No DELETE requests fire**:
1. Zero `DELETE /knowledge-base/{id}` requests are recorded

**Observation 2 — Rows preserved + selection intact**:
1. Both rows remain in the table
2. The floating bar still shows them selected

---

### TC-EDGE-019: Status polling lifecycle starts and stops appropriately (KB-042)

**Action**:
1. Upload a file (badge `Processing`)
2. Wait until poll yields `Active`

**Observation 1 — Poll fires every 4 s while any row is Processing**:
1. The status polling interval triggers refetches every ~4 s
2. Once no `processing` rows remain in the visible page, polling stops

---

### TC-EDGE-020: Save changes disabled until a real change is made (KB-045)

**Action**:
1. Open Edit modal
2. Do NOT change file_name or pick a new file

**Observation 1 — Save disabled**:
1. `Save changes` has `disabled` attribute
2. Becomes enabled only after a real change (name OR file)

---

### TC-A11Y-001: Tab order through upload modal reaches every control (KB-046)

**Action**:
1. Open `Add Sources`
2. Tab through

**Observation 1 — Tab order**:
1. Order is: Agent select → Drop zone → first file remove → CTA → Cancel
2. Every interactive control is reachable

---

### TC-A11Y-002: Drop zone keyboard activation opens file picker (KB-047)

**Preconditions**: Drop zone focused.

**Action**:
1. Press Enter (or Space)

**Observation 1 — File picker opens**:
1. The native file picker is invoked

---

### TC-A11Y-003: Remove buttons expose per-file accessible names (KB-048)

**Action**:
1. Open upload modal with queued files
2. Inspect file row remove buttons

**Observation 1 — aria-label per file**:
1. Each remove button has `aria-label="Remove <file name>"`

---

### TC-A11Y-004: Status badges include readable text (KB-049)

**Action**:
1. Observe status badges

**Observation 1 — Text label, not only color**:
1. Active / Processing / Failed all render as readable text

---

### TC-A11Y-005: Upload progress announced via aria-live (KB-050)

**Action**:
1. Submit a multi-file upload

**Observation 1 — aria-live region**:
1. Progress text (e.g. `Uploading 2 of 5`) is inside an `aria-live="polite"` element

---

### TC-A11Y-006: KB modal traps focus and restores on close (KB-051)

**Action**:
1. Open the Add Sources modal
2. Tab repeatedly
3. Press Esc

**Observation 1 — Trapped inside**:
1. Tab cycles inside the modal
2. Focus does not escape

**Observation 2 — Restored on close**:
1. After Esc, focus returns to the `Add Sources` button (or originating row trigger)

---

### TC-A11Y-007: Error toast is announced via aria-live (KB-052)

**Action**:
1. Trigger an error toast

**Observation 1 — aria-live**:
1. Toast has `role="alert"` or `aria-live`
2. Screen readers announce the title

---

### TC-A11Y-008: Enter in file_name field submits when dirty (KB-053)

**Preconditions**: Edit modal with valid (dirty) file_name.

**Action**:
1. Press Enter in the file_name field

**Observation 1 — Save fires**:
1. `Save changes` action triggers (PATCH request fires)

---

### TC-A11Y-009: Bulk action bar is keyboard reachable (KB-054)

**Preconditions**: At least one row selected.

**Action**:
1. Tab to the floating action bar

**Observation 1 — Clear + Delete reachable**:
1. Both `Clear` and `Delete` are reachable via Tab
2. Both are real `<button>` elements

---

### TC-FULL-001: End-to-end knowledge base lifecycle (KB-FULL)

**Preconditions**:
- Test user provisioned; seed an `__e2e__` agent via the backend admin API.

**Action**:
1. Authenticate via `loginViaUI`
2. Visit `/knowledge-base`
3. Open `Add Sources` and upload a valid `__e2e__ policy.pdf` (1 MB)
4. Wait for status poll to flip the badge from `Processing` to `Active`
5. Click the row to open the detail modal
6. Click `Edit`, rename to `__e2e__ renamed.pdf`, click `Save changes`
7. Close the detail modal
8. Search `name:__e2e__`
9. Search `name:does-not-exist`
10. Clear filters
11. Click the trash icon on the seeded row, confirm delete

**Observation 1 — Step 2 — List loads**:
1. h1 `Knowledge Base` visible
2. `Add Sources` CTA visible

**Observation 2 — Step 3 — Upload progress + success**:
1. Progress UI advances during upload
2. Toast title `Document uploaded` appears
3. New row visible with `Processing` badge

**Observation 3 — Step 4 — Status poll flips badge**:
1. Within polling intervals, badge becomes `Active`

**Observation 4 — Step 5 — Detail modal**:
1. Agent name, file size, and dates visible

**Observation 5 — Step 6 — Rename success**:
1. Toast title `Document renamed`
2. Row reflects the new file_name

**Observation 6 — Step 8 — Search filter**:
1. Only the seeded doc is visible

**Observation 7 — Step 9 — No-matches state**:
1. Empty state reads `No documents match your filters`

**Observation 8 — Step 10 — Clear filters**:
1. List refetches with all rows

**Observation 9 — Step 11 — Single delete**:
1. Toast title `Document deleted`
2. Row removed from table

**Cleanup** (in `try/finally`):
1. Delete the seeded `__e2e__` agent via the backend admin API
2. Clear cookies and localStorage

---

## Edge Cases (each appears as a `TC-EDGE-*` / `TC-LOADING-*` / `TC-NAV-*` / `TC-ERROR-*` test case above)

- [x] Unauthenticated access → see TC-NAV-001
- [x] No agents in org → see TC-ERROR-001 (Agent select disabled)
- [x] File >100 MB or unsupported extension → see TC-ERROR-002 / TC-ERROR-003
- [x] Same name+size file dropped twice → see TC-ERROR-004
- [x] Upload errors mid-batch → see TC-ERROR-009
- [x] Status polling 4 s interval lifecycle → see TC-EDGE-019
- [x] Failed document with AlertTriangle alert → see TC-HAPPY-012
- [x] Detail modal "View file" hidden when no URL → see TC-HAPPY-007 Observation 2
- [x] Bulk delete partial failure keeps failed IDs selected → see TC-ERROR-017
- [x] Long file names → middle ellipsis — covered by render observations (display only)
- [x] Document linked to deleted agent renders "Unknown agent" → covered by TC-HAPPY-007 (render only) ⚠ unverified specific copy
- [x] Search + filter combination zero results → see TC-EDGE-009
- [x] EditDocument no changes → see TC-EDGE-020
- [x] Bulk delete partial-failure copy → see TC-ERROR-017
- [x] Status polling lifecycle starts/stops → see TC-EDGE-019
- [x] sessionStorage key collision — verified: KB does not write to sessionStorage
- [x] Reserved URL segments (no sub-routes) → 404 via Next.js (out of scope here)
- [x] Oversize / unsupported rejection BEFORE network → see TC-ERROR-002 / TC-ERROR-003
- [x] Processing → ready status flip timing (≤ 4 s) → see TC-EDGE-017 / TC-EDGE-019
- [x] Upload partial failure modal stays open with only failed files → see TC-ERROR-009
- [x] All-failed upload surfaces handleApiError(lastError) → see TC-ERROR-005 / TC-ERROR-006

---

## Business Rules

- Documents are scoped to a single agent (`agent_id` is required on upload). Cross-agent reuse is not supported in the current UI.
- Supported MIME types: PDF, DOCX, TXT, CSV, JSON, HTML. The server-side ingestion pipeline also enforces this.
- The frontend polls only while at least one visible row is "Processing"; polling stops automatically.
- Renaming does not invalidate chunks or embeddings — only `PATCH /…/file` triggers reprocessing.
- The retry endpoint reuses the same `id`/R2 object; users can retry a failed document repeatedly without recreating it.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Drop zones activatable via Enter/Space when focused → see TC-A11Y-002
- [x] File rows expose remove button with `aria-label="Remove <file name>"` → see TC-A11Y-003
- [x] Status badges include text label, not only color → see TC-A11Y-004
- [x] Upload progress announced via `aria-live="polite"` → see TC-A11Y-005
- [x] Modals trap focus and restore it on close → see TC-A11Y-006
- [x] Search bar input has an associated label or aria-label → covered in UI elements + TC-A11Y-001
- [x] Bulk action bar keyboard reachable → see TC-A11Y-009
- [x] Error toast announced via aria-live → see TC-A11Y-007
- [x] Enter in file_name field submits when dirty → see TC-A11Y-008
