# Feature Doc: Knowledge Base

Feature documentation for the Knowledge Base page. Used by
`/generate-tests knowledge-base` (or `--docs e2e/ux_flow_docs/knowledge-base.md`) to
ensure all user cases are covered.

The Knowledge Base lets agent owners upload documents (PDF, DOCX, TXT, CSV,
JSON, HTML) and associate them with an agent so the voice pipeline can answer
from those documents at call-time via RAG (retrieval-augmented generation).

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

## User Workflow Steps

Step-by-step actions per major flow. Used to derive `test(...)` blocks in `e2e/dashboard/knowledge-base.spec.ts`. Selectors prefer `getByRole`, `getByPlaceholder`, `getByText`. Toast assertions use `page.locator('[data-sonner-toast]')`.

**WF-1: Browse the document list** (positive — US-1)

1. User authenticates via `loginViaUI(page)` and navigates to `/knowledge-base` → expected: heading "Knowledge Base" visible, "Add Sources" button visible, search bar visible with placeholder `Search documents… (e.g. name:resort, status:ready)`.
2. With `/knowledge-base/list` returning two items → expected: table renders 2 rows, status badges read "Active" and "Processing", "Last updated" column shows formatted dates.
3. User clicks the column header "Name / Type" → expected: `/knowledge-base/list` re-fires with `sort_by: "file_name", sort_order: "asc"`.
4. User changes page size to 50 → expected: `/knowledge-base/list` re-fires with `page_size: 50, page: 1`.

**WF-2: Upload a single document** (positive — US-2)

1. User clicks "Add Sources" → expected: modal with title "Add sources" opens, primary button reads "Upload document" and is disabled.
2. User selects an agent from the "Agent" dropdown → expected: button still disabled (no file yet).
3. User drops `policy.pdf` (2 MB) on the drop zone → expected: a file row appears with the filename, size "2.0 MB", and an X (remove) button; primary button enables.
4. User clicks "Upload document" → expected: `POST /knowledge-base` fires multipart with `agent_id` + `file`; on 201 the modal closes, table refetches, toast title `Document uploaded`, description `Your documents are now part of the knowledge base.`

**WF-3: Upload multiple documents with progress** (positive — US-2)

1. User opens "Add Sources" modal, picks an agent, drops 3 valid files → expected: primary button reads `Upload 3 files`, queue shows 3 rows.
2. User clicks `Upload 3 files` → expected: progress UI shows `Uploading 1 of 3` then `2 of 3` then `3 of 3`, the percentage bar advances, three sequential `POST /knowledge-base` calls fire.
3. All three succeed → expected: modal closes, toast title `3 documents uploaded`.

**WF-4: Open document details** (positive — US-3)

1. User clicks a row whose status is "Active" → expected: "Document details" modal opens.
2. Modal shows: file name, type badge (e.g. PDF), status badge ("Active"), Agent row, File size, Uploaded, Last updated, footer "Delete" (left) + "Edit" / "View file" (right). "View file" hidden when `url` is null.
3. User clicks "View file" → expected: `window.open` invoked with the URL in a new tab.

**WF-5: Edit — rename only** (positive — US-4)

1. User opens detail modal → clicks "Edit" → expected: `EditDocument` modal opens with `file_name` input pre-filled.
2. User clears and types `renamed.pdf`, leaves drop zone untouched → expected: "Save changes" enables.
3. User clicks "Save changes" → expected: `PATCH /knowledge-base/{id}` body `{ "file_name": "renamed.pdf" }`; on 200, toast title `Document renamed`, table refetches.

**WF-6: Edit — replace file (with rename)** (positive — US-4)

1. From the edit modal, user drops `policy_v2.pdf` → expected: drop zone is replaced by a single-file preview row showing the new file name + "replaces current file"; if the user had not edited the name field, the name field auto-syncs to `policy_v2.pdf`.
2. User clicks "Save changes" → expected: `PATCH /knowledge-base/{id}/file` multipart with `file` + optional `file_name`; on 200, toast title is `File replaced & renamed` (if name changed) or `File replaced` otherwise, description `Changes saved successfully.`

**WF-7: Retry a failed document** (positive — US-5)

1. With one row showing "Failed" status → expected: inline retry icon visible only on that row.
2. User clicks the inline retry icon → expected: `POST /knowledge-base/{id}/reprocess` fires; toast title `Retrying`, description `Document processing has been restarted.`; row badge flips to "Processing" within 4 s of the next poll.
3. Alternative entry: from the detail modal, the "Processing failed" alert renders `meta_data.error` plus a "Retry processing" button which calls the same endpoint.

**WF-8: Single-row delete** (positive — US-6)

1. User clicks the trash icon on a row → expected: confirm modal opens with title `Delete document` and description `Are you sure you want to delete "<file_name>"? This action cannot be undone.`
2. User clicks confirm `Delete` → expected: `DELETE /knowledge-base/{id}` fires; on 200, toast title `Document deleted`, the row disappears.

**WF-9: Bulk delete** (positive — US-6)

1. User checks 3 rows → expected: floating selection bar appears with `3 documents selected`, "Clear", "Delete" buttons.
2. User clicks "Delete" → expected: confirm modal title `Delete documents`, description `Delete 3 selected documents? This action cannot be undone.`
3. User confirms → expected: 3 parallel `DELETE /knowledge-base/{id}` calls fire via `Promise.allSettled`; if all succeed, toast title `3 documents deleted`, selection cleared.

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

## Success Scenarios

**PS-1: List loads with documents** (US-1)

- Preconditions: Logged in; mock `**/knowledge-base/list` returns 2 items including one `ready` and one `processing`.
- Steps: navigate to `/knowledge-base`.
- Expected outcome: heading visible, 2 rows in the table, status badges read "Active" and "Processing", search placeholder visible, "Add Sources" button visible.
- Mock API success body:
```json
{
  "items": [
    {"id": "8a3f1c12-2b9e-4a51-9b3a-5fe2dc4d7a01", "file_name": "refund_policy.pdf", "file_type": "application/pdf", "size_bytes": 245678, "status": "ready", "agent_id": "a-1", "url": "https://r2.example.com/...", "meta_data": {}, "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:02:00+00:00"},
    {"id": "550e8400-up-002", "file_name": "product_faq.docx", "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "size_bytes": 84231, "status": "processing", "agent_id": "a-1", "url": null, "meta_data": {}, "created_at": "2026-05-27T10:05:00+00:00", "updated_at": "2026-05-27T10:05:00+00:00"}
  ],
  "total": 2, "page": 1, "page_size": 20
}
```

**PS-2: Empty list shows the no-docs empty state** (US-1)

- Preconditions: mock list returns `{"items": [], "total": 0, "page": 1, "page_size": 20}`.
- Expected: "No documents yet" heading + descriptive subtitle + "Add Sources" button.

**PS-3: Single-file upload success** (US-2)

- Preconditions: agents atom has ≥1 agent; mock `POST **/knowledge-base` returns 201.
- Steps: open Add Sources → select agent → drop `policy.pdf` (1 MB) → click "Upload document".
- Expected: modal closes, table refetches, toast `Document uploaded` / `Your documents are now part of the knowledge base.`
- Mock API success body:
```json
{
  "id": "8a3f1c12-2b9e-4a51-9b3a-5fe2dc4d7a01",
  "file_name": "policy.pdf",
  "file_type": "application/pdf",
  "size_bytes": 1048576,
  "purpose": "kb_document",
  "status": "processing",
  "meta_data": {},
  "created_at": "2026-06-17T10:14:32.118500+00:00",
  "updated_at": "2026-06-17T10:14:32.118500+00:00",
  "url": "https://r2.example.com/knowledge-base/org/.../policy.pdf?X-Amz-Signature=..."
}
```

**PS-4: Multi-file upload success** (US-2) — 3 files; assertion targets show `Uploading 1 of 3`, `Uploading 2 of 3`, `Uploading 3 of 3`; final toast `3 documents uploaded`.

**PS-5: Rename a document** (US-4) — `PATCH /knowledge-base/{id}` body `{"file_name":"renamed.pdf"}` returns 200; toast `Document renamed`.

**PS-6: Replace file with rename** (US-4) — `PATCH /knowledge-base/{id}/file` multipart returns 200 with `status: "processing"`; toast `File replaced & renamed` / `Changes saved successfully.`
```json
{"id":"8a3f1c12-...","file_name":"refund_policy_v3.pdf","file_type":"application/pdf","size_bytes":312456,"status":"processing","url":"https://r2.example.com/...","updated_at":"2026-05-27T10:15:00+00:00"}
```

**PS-7: Reprocess success** (US-5) — `POST /knowledge-base/{id}/reprocess` returns 202; toast `Retrying` / `Document processing has been restarted.`; row badge becomes "Processing".

**PS-8: Single delete success** (US-6) — `DELETE /knowledge-base/{id}` returns 200 `{"ok": true}`; toast `Document deleted`.

**PS-9: Bulk delete success** (US-6) — 3 parallel deletes all 200; toast `3 documents deleted`; selection cleared.

**PS-10: View file opens URL** (US-3) — clicking "View file" calls `window.open(meta_data.url, '_blank')` (assert via `page.context().waitForEvent('page')`).

---

## Failure Scenarios

**FS-1: Upload blocked when no agent selected** — preconditions: file dropped, agent NOT chosen → expected: "Upload document" button stays `disabled`, no network call. Inline error: none (button-level guard only).

**FS-2: Oversize file (>100 MB) rejected at queue time** — drop a file with `size > 104857600` → expected: toast title `Too large: <name>`, description `Maximum file size is 100 MB`; file does NOT appear in the queue; no `POST /knowledge-base` request.

**FS-3: Unsupported MIME / extension** — drop `evil.exe` → expected: toast title `Unsupported: evil.exe`, description `Supported: pdf, txt, csv, html, json, docx`; no queue entry; no network call.

**FS-4: Duplicate file in queue** — drop `a.pdf` then drop the same `a.pdf` (same name + size) → expected: still 1 row in the queue; no toast.

**FS-5: Upload server error (500 / network failure)** — single file upload, mock `POST **/knowledge-base` returns 500 (or `route.abort('failed')`) → expected: modal stays open with the failed file still in queue, toast comes from `handleApiError` — title is `Something went wrong. Please try again.` (default) or the server `detail` string.

**FS-6: Upload — agent missing config (409)** — mock returns 409:
```json
{"detail": "Agent has no published configuration yet. Save and publish the agent before uploading knowledge base documents."}
```
Expected: toast title is that exact `detail` string (rendered by `handleApiError`); modal stays open, failed file remains in queue.

**FS-7: Upload — validation error (422 missing file)** — mock returns 422 with `{"detail":[{"loc":["body","file"],"msg":"field required","type":"value_error.missing"}]}` → expected: `handleApiError` toast with default message (detail is an array, not a string); file remains in queue for retry.

**FS-8: Upload — unauthorized (401)** — mock returns 401 `{"detail":"Invalid token"}` → expected: toast title is `Invalid token`.

**FS-9: Upload partial success (some succeed, some fail)** — 3 files; 2 succeed (201) and 1 returns 500 → expected: only the failed file remains in the queue; toast title `2 of 3 uploaded`, description `1 failed — retry the remaining files.` Modal stays open. Agent select is NOT cleared.

**FS-10: Rename — `file_name too long`** — `PATCH /knowledge-base/{id}` returns 400 `{"detail":"file_name too long (max 512)"}` → expected: toast title `file_name too long (max 512)`; modal stays open; "Save changes" re-enables.

**FS-11: Rename — upload not found (404)** — returns 404 `{"detail":"Upload not found"}` → expected: toast title `Upload not found`.

**FS-12: Replace file — empty file (400)** — returns 400 `{"detail":"Empty file"}` → expected: toast title `Empty file`; modal stays open; new file still listed.

**FS-13: Reprocess — no stored file (400)** — `POST /knowledge-base/{id}/reprocess` returns 400 `{"detail":"Upload has no stored file to reprocess"}` → expected: toast title that detail string; row status stays "Failed".

**FS-14: Reprocess — document not found (404)** — returns 404 `{"detail":"Document not found"}` → expected: toast title `Document not found`.

**FS-15: Single delete failure (500)** — returns 500 → expected: confirm modal closes, but the row remains; `handleApiError` toast.

**FS-16: Bulk delete — all fail** — 3 deletes all return 500 → expected: toast title `Bulk delete failed`, description `No documents were deleted.`; floating selection bar still shows all 3 selected.

**FS-17: Bulk delete — partial failure (1 of 3 fails)** — 2 succeed, 1 fails → expected: toast title `Partial delete`, description `2 of 3 deleted. 1 failed — refresh and try again.`; the floating selection bar now shows `1 document selected` (only failed IDs).

**FS-18: Unauthorized list (401)** — `POST **/knowledge-base/list` returns 401 → expected: middleware does NOT auto-redirect (request already authenticated by cookie); list shows empty state with no-matches/no-docs depending on `hasActiveFilters` flag. Verify there is no infinite spinner.

**FS-19: Validation 422 on list** — returns:
```json
{"detail":[{"loc":["body"],"msg":"value is not a valid dict","type":"type_error.dict"}]}
```
Expected: list state remains empty; no crash (component does not throw on missing `items`).

**FS-20: Unauthenticated access** — no `tone_access_token` cookie → `/knowledge-base` request triggers `src/middleware.ts` redirect to `/auth/login?redirect=%2Fknowledge-base`.

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

## Edge Cases

- [ ] Unauthenticated access → middleware redirect
- [ ] No agents in org → Agent select is disabled; upload is blocked with a helper hint
- [ ] File >100 MB or unsupported extension → toast error, file rejected from queue
- [ ] Same name+size file dropped twice → deduplicated silently
- [ ] Upload errors mid-batch → partial-success toast; successful uploads still added
- [ ] Status polling: 4-second interval starts when any row is "Processing" and stops when none remain
- [ ] Failed document → AlertTriangle in detail modal with `meta_data.error`; "Retry processing" available
- [ ] Detail modal "View file" hidden when no URL is present
- [ ] Bulk delete partial failure → floating bar keeps the failed IDs selected for retry
- [ ] Long file names → middle ellipsis (preserves the extension): "Voice AI Testing Platfo…uation.pdf"
- [ ] Document linked to a deleted agent → renders as "Unknown agent"
- [ ] Search + filter combination returning zero results → no-matches empty state (different from no-docs empty state)
- [ ] EditDocument with no changes → "Save changes" disabled
- [ ] Bulk delete partial failure → toast title `Partial delete`, description `N of M deleted. K failed — refresh and try again.`; failed IDs remain selected in the floating bar
- [ ] Status polling lifecycle → `pollWhile` interval starts the moment a `processing` row enters the visible page, stops once the response has no `processing` row left; switching to a filter that hides processing rows also stops the poll
- [ ] sessionStorage key collision → only `mcp-form-oauth-draft` is used by MCP; KB does not write to sessionStorage. Verify no KB modal accidentally writes to that key.
- [ ] Reserved URL segments — KB has no reserved sub-routes; `/knowledge-base/upload` etc. should 404 via Next.js
- [ ] Oversize / unsupported file rejection messaging surfaces *before* upload begins (no network call). The toast shows the offending file name in the title.
- [ ] Processing → ready status flip timing — after `reprocess`, the row stays "Processing" until the next poll cycle (≤ 4 s) returns `status: "ready"`
- [ ] Upload partial failure → modal stays open with only the failed files in the queue (succeeded files are removed), toast title `N of M uploaded`, description `K failed — retry the remaining files.`
- [ ] All-failed upload → toast comes from `handleApiError(lastError)`, so title is the server's `detail` string (e.g. `Agent has no published configuration yet…`)

---

## Business Rules

- Documents are scoped to a single agent (`agent_id` is required on upload). Cross-agent reuse is not supported in the current UI.
- Supported MIME types: PDF, DOCX, TXT, CSV, JSON, HTML. The server-side ingestion pipeline also enforces this.
- The frontend polls only while at least one visible row is "Processing"; polling stops automatically.
- Renaming does not invalidate chunks or embeddings — only `PATCH /…/file` triggers reprocessing.
- The retry endpoint reuses the same `id`/R2 object; users can retry a failed document repeatedly without recreating it.

---

## Accessibility Requirements

- [ ] Drop zones are activatable via Enter/Space when focused
- [ ] File rows expose a remove button with `aria-label="Remove <file name>"`
- [ ] Status badges include a text label, not only color (Active / Processing / Failed)
- [ ] Upload progress is announced via `aria-live="polite"` so screen readers hear "Uploading 2 of 5"
- [ ] Modals trap focus and restore it on close (Radix/shadcn default)
- [ ] Search bar input has an associated label or aria-label
- [ ] Bulk action bar is keyboard reachable; "Delete" is a real `<button>` with an accessible name

---

## Appended Scenarios (gap-fill, ID prefix `KB-`)

These rows extend the PS/FS coverage with auth/error-state/network/a11y/list-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `knowledge-base.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-001 | Visit `/knowledge-base` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fknowledge-base` | `unauthenticated visit redirects to login` |
| KB-002 | Visit `/knowledge-base` with an expired token cookie | Middleware 307 → `/auth/login?redirect=%2Fknowledge-base`; expired cookie cleared | `expired token redirects to login and clears cookie` |
| KB-003 | Member role attempts upload | Either upload allowed (org policy) OR backend 403 with toast `Admin or Owner role required` | `member role upload behavior follows org policy` |
| KB-004 | Logged-in user from another org opens a stale link | `POST /knowledge-base/list` returns rows scoped to the new org; old doc ids 404 on edit/delete | `org switch scopes the document list correctly` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-005 | `POST /knowledge-base/list` returns 400 (malformed filter) | Empty list state; toast surfaces backend `detail`; no crash | `list 400 surfaces detail toast and renders empty list` |
| KB-006 | Token expires between page load and upload submit → 401 | Toast `Invalid token`; modal stays open; queue preserved | `upload 401 surfaces error toast without redirect` |
| KB-007 | 403 forbidden on delete (member trying owner-only action) | Toast surfaces backend `detail`; row remains | `delete 403 surfaces forbidden toast` |
| KB-008 | Delete a document already removed → 404 | Toast `Upload not found`; subsequent refetch removes the stale row | `delete 404 surfaces not-found toast` |
| KB-009 | Upload conflict — agent has no published config (409) | Toast `Agent has no published configuration yet…`; modal stays open with failed file queued | `upload 409 keeps modal open with failed file` |
| KB-010 | 500 server error on upload | Modal stays open; failed file remains queued; toast `Internal Server Error` OR default | `upload 500 keeps modal open with failed queue` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-011 | Offline / network failure during upload | Modal stays open; toast `Something went wrong. Please try again.`; failed file still queued | `upload network failure preserves queue` |
| KB-012 | Slow `POST /knowledge-base` (>3s) | Progress UI shows `Uploading 1 of 1` + percentage bar; primary CTA disabled | `slow upload shows progress with disabled cta` |
| KB-013 | Slow `POST /knowledge-base/list` (>3s) | Skeleton rows visible the whole time; Add Sources button remains enabled | `slow list keeps skeleton without blocking add sources` |
| KB-014 | Concurrent reprocess + status poll | Status poll yields the latest backend state; UI does not flip between Processing/Failed | `concurrent reprocess and poll converges on latest state` |
| KB-015 | Bulk delete with network failure mid-batch | `Promise.allSettled` resolves; partial-success toast `Partial delete`; failed IDs remain selected | `bulk delete partial network failure surfaces partial toast` |

### Input edge cases (upload + edit)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-016 | Whitespace-only file_name on edit | "Save changes" disabled (canSave false); defensive toast `Name required` if reached | `whitespace-only file name is rejected` |
| KB-017 | File name with leading/trailing whitespace | Sent as-is OR trimmed; round-trip preserves the displayed value | `file name preserves or trims whitespace consistently` |
| KB-018 | File name with special chars + emoji + unicode | Accepted; rendered safely in the table and modal (no XSS) | `file name accepts unicode and html-ish characters without xss` |
| KB-019 | File name > 512 chars | Backend 400 `file_name too long (max 512)`; toast surfaces detail | `very long file name surfaces backend length error` |
| KB-020 | Drop wrong file type (`.exe`) | Toast `Unsupported: <name>` + `Supported: pdf, txt, csv, html, json, docx`; queue unchanged | `wrong file type rejected before upload` |
| KB-021 | Drop oversize file (>100 MB) | Toast `Too large: <name>` + `Maximum file size is 100 MB`; queue unchanged | `oversize file rejected before upload` |
| KB-022 | Drop empty file (0 bytes) | Either queue rejects OR backend 400 `Empty file`; toast surfaces detail | `empty file rejected before or during upload` |
| KB-023 | Drop valid file round-trips | After successful upload, doc appears in list; clicking opens detail with the same metadata | `valid file uploaded round-trips into the list` |
| KB-024 | Same name+size duplicate in queue | Silently deduplicated; queue length unchanged; no toast | `duplicate file in queue is deduped silently` |
| KB-025 | Token search with whitespace-only value | Sent as empty; list reverts to default | `whitespace-only search treated as empty` |
| KB-026 | Token search with regex-special characters | Sent verbatim; backend treats as literal substring; no crash | `regex-special search characters do not crash list` |
| KB-027 | Token search with > 500 characters | Either accepted or backend truncates; no client crash | `very long search does not crash the page` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-028 | Empty list with no documents | "No documents yet" + "Add Sources" CTA | `empty list renders the no-docs empty state` |
| KB-029 | Empty list under active filters | "No documents match your filters" + clear-filters CTA | `filtered list with no matches renders no-results state` |
| KB-030 | Pagination — first page | Prev disabled, Next enabled when more pages exist | `pagination disables prev on the first page` |
| KB-031 | Pagination — last page | Next disabled, Prev enabled | `pagination disables next on the last page` |
| KB-032 | Sort by Name / Type | `POST /knowledge-base/list` fires with `sort_by: 'file_name'` then toggles direction | `sort by name cycles asc and desc` |
| KB-033 | Sort by Last updated | `POST /knowledge-base/list` fires with `sort_by: '-updated_at'` | `sort by last updated orders descending` |
| KB-034 | Filter chip removable | Clicking chip's X removes that filter and re-fetches | `removing a filter chip refetches without it` |
| KB-035 | "Clear all filters" CTA | Resets every active filter; list refetches | `clear all filters resets filter state` |
| KB-036 | Page size change resets page to 1 | Each new page_size value re-fires `POST /knowledge-base/list` with `page: 1` | `page size change resets to page 1` |

### Knowledge-base-specific

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-037 | Upload progress shows N of M | `Uploading 1 of 3` → `2 of 3` → `3 of 3`; percentage bar advances | `multi-upload progress shows N of M and percentage` |
| KB-038 | Embedding/indexing status reflected in UI | After upload, row status starts `Processing` (amber pulsing); flips to `Active` or `Failed` after polling | `status badge reflects ingestion lifecycle` |
| KB-039 | Document preview/download via "View file" | Opens `meta_data.url` in a new tab; hidden when URL is null | `view file opens document url in a new tab` |
| KB-040 | Bulk delete confirmation modal | Title `Delete documents`, description includes count and warning copy; Cancel keeps rows | `bulk delete confirmation cancel preserves rows` |
| KB-041 | Bulk delete partial-failure UI | Floating bar keeps failed IDs selected; toast `Partial delete` with N/M counts | `bulk delete partial failure leaves failed ids selected` |
| KB-042 | Status polling — every 4s while any row is processing | Poll stops once no `processing` row remains in the visible page | `status polling lifecycle starts and stops appropriately` |
| KB-043 | Failed document — Retry inline icon | `POST /knowledge-base/{id}/reprocess` fires; status flips to Processing | `retry inline icon triggers reprocess` |
| KB-044 | Failed document — Retry from detail modal | Same endpoint; AlertTriangle alert renders `meta_data.error` | `retry from detail modal triggers reprocess with error context` |
| KB-045 | Replace-file edit dirty check | "Save changes" stays disabled until file_name or replace-file changes | `save changes disabled until a real change is made` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-046 | Tab order through upload modal | Agent select → Drop zone → first file remove → CTA → Cancel — reachable in order | `tab order through upload modal reaches every control` |
| KB-047 | Drop zone activates via Enter / Space when focused | Opens the file picker | `drop zone keyboard activation opens file picker` |
| KB-048 | File row remove button has `aria-label="Remove <file name>"` | Screen readers can announce per-row remove | `remove buttons expose per-file accessible names` |
| KB-049 | Status badges include text label, not only color | Active / Processing / Failed all render readable text | `status badges include readable text` |
| KB-050 | Upload progress announced via `aria-live="polite"` | Screen readers hear "Uploading 2 of 5" without manual focus | `upload progress announced via aria-live` |
| KB-051 | Modal traps focus and restores on close | Focus stays inside; Esc closes; focus returns to Add Sources / row trigger | `kb modal traps focus and restores on close` |
| KB-052 | Error toast has `role="alert"` / aria-live | Screen readers announce the toast title | `error toast is announced via aria-live` |
| KB-053 | Submit via Enter in the file_name field of EditDocument | Triggers Save changes when canSave is true | `Enter in file name field submits when dirty` |
| KB-054 | Bulk action bar is keyboard reachable | Floating bar's Clear + Delete reachable via Tab; both real buttons | `bulk action bar is keyboard reachable` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-055 | Click "View file" opens in a new tab | New tab loads `meta_data.url`; original tab stays on `/knowledge-base` | `view file opens new tab without leaving list` |
| KB-056 | Browser back after opening detail modal | Modal closes; URL unchanged; list state preserved | `browser back closes detail modal without leaving page` |
| KB-057 | Reload `/knowledge-base` | Page reloads with the list intact; no auth redirect for authenticated user | `reload preserves the knowledge base list` |
| KB-058 | Cross-link to attached agent | Detail modal renders the agent name; clicking it navigates to `/agents/edit/<type>/<id>/overview` if linked | `agent link in detail navigates to the agent page` |

### Full lifecycle (`KB-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| KB-FULL | Authenticate via `loginViaUI` → seed an `__e2e__` agent → visit `/knowledge-base` → assert headings + Add Sources CTA → upload a valid `__e2e__ policy.pdf` (1 MB) via Add Sources modal → assert progress UI and `Document uploaded` toast → list refreshes and the new row appears with `Processing` badge → wait for status poll to flip badge to `Active` → click row → assert detail modal shows agent name, file size, dates → click Edit → rename to `__e2e__ renamed.pdf` → Save → assert `Document renamed` toast → close detail → search `name:__e2e__` and assert only the seeded doc visible → search `name:does-not-exist` and assert "No documents match your filters" state → clear filters → trash icon → confirm delete → assert `Document deleted` toast and row removed → cleanup the seeded agent via API in the same `try/finally` block | All endpoints fire with the expected payloads; uploads round-trip through the indexing lifecycle; cleanup runs in the same test body even if assertions fail | `walks the entire knowledge base flow end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| KB-001..004 | FS-20 (auth gating) | Adds expired-token + member + org-switch cases |
| KB-005..010 | FS-5..FS-17 | Standardises 400/401/403/404/409/500 paths |
| KB-011..015 | (new) | Network resilience + concurrent poll + bulk-delete partial failure |
| KB-016..027 | FS-2..FS-4, FS-10..FS-12 | Adds whitespace, special-char, length, file-type, empty-file edges |
| KB-028..036 | PS-1, PS-2 | Promotes pagination/sort/empty-state to scenarios |
| KB-037..045 | PS-3..PS-9 | Promotes KB-specific upload progress/preview/bulk-delete/retry to scenarios |
| KB-046..054 | Accessibility section | Promotes a11y bullets to scenarios |
| KB-055..058 | Navigation table | Adds reload + new-tab + cross-feature links |
| KB-FULL | (new) | Single-test sweep of upload → list → search → delete |
