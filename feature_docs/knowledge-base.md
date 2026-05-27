# Knowledge Base — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

The **Knowledge Base** lets users upload documents (PDF, DOCX, TXT) to an [[agents|Agent]] for runtime RAG (retrieval-augmented generation). The pipeline is: upload → R2 object storage → text extraction → recursive character chunking → OpenAI embeddings → `knowledge_base_chunks` rows backed by `pgvector` for cosine-similarity lookup at call-time.

At runtime, `core/services/document_tool_service.py` registers a `read_document` tool on the agent's Pipecat pipeline; when the LLM calls it, the service runs a top-3 cosine-distance query against the agent's chunks and returns the matched text.

- **Target users**: agent owners who want their voice agent to answer from a private corpus (product docs, FAQ, policies).
- **Problem solved**: a turnkey RAG layer per agent — no separate vector DB to operate, no embedding pipeline to wire.

Cross-links: [[agents]] (each agent can have many uploads), [[voice-pipeline]] (runtime RAG step), [[model-providers]] (OpenAI key is the embeddings provider today).

## 2. User stories & use cases

- As an agent owner, I want to upload a PDF so my agent can answer questions about it.
- As an agent owner, I want to see the list of documents already attached to my agent.
- As an agent owner, I want to rename a document or replace its file without losing the chunk history.
- As an agent owner, I want to delete a document and have its chunks + R2 blob removed.
- As a caller (indirect user), I want the agent to retrieve the most relevant passage from the KB and incorporate it into its response.

Typical flow: Agent owner → `/knowledge-base` → "Upload" → picks PDF + agent_config target → backend writes to R2 → schedules background processing → status flips from `processing` → `ready` → next call uses the chunks.

## 3. Functional requirements

- **`POST /knowledge-base`**: multipart upload. Writes to R2 (`uploads/{org_id}/{upload_id}`), creates `Upload` row (`purpose=kb_document`, status=`processing`), creates `AgentKnowledgeBase` join row, and schedules `DocumentProcessingService.process_upload` via FastAPI `BackgroundTasks`.
- **`POST /knowledge-base/list`**: paginated list with search/sort/filter, scoped to the agent or org.
- **`PATCH /knowledge-base/{upload_id}`**: rename document.
- **`PATCH /knowledge-base/{upload_id}/file`**: replace the underlying file (re-chunks + re-embeds).
- **`DELETE /knowledge-base/{upload_id}`**: delete the document — removes chunks + R2 blob + `AgentKnowledgeBase` rows.
- **Signed URLs**: `_signed_url(file_path)` produces short-lived R2 presigned URLs for downloads.
- **Processing pipeline** (`DocumentProcessingService.process_upload`):
  1. Download from R2.
  2. Text extract (PyPDF2 / python-docx / utf-8 fallback) via `core/services/text_extraction_service.py`.
  3. Chunk via LangChain `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap).
  4. Embed via OpenAI `text-embedding-3-small` in batches of 100.
  5. Insert `KnowledgeBaseChunk` rows (`pgvector` `Vector(1536)`).
  6. Mark `Upload.status = 'ready'` (or `'error'` with error message).
- **Runtime RAG** (`core/services/document_tool_service.py`):
  - Registers `read_document` tool dynamically at pipeline boot if agent has KB uploads.
  - Tool executes `SELECT content FROM knowledge_base_chunks WHERE agent_id = X ORDER BY embedding <=> $query LIMIT 3` (cosine distance via `<=>`).

### Edge cases & failure modes

- **⚠ EE controller does NOT schedule processing**: `ee/api/v1/knowledge_base.py` sets `status="ready"` immediately on upload and never calls `DocumentProcessingService.process_upload`. Uploads in EE are never chunked or embedded. Either intentional (EE expects an external pipeline) or a critical bug.
- **⚠ R2 leak on 409**: upload writes to R2 *before* checking `AgentConfig`. If the agent has no config, the 409 path orphans the R2 blob with no cleanup.
- **⚠ Postman collection drift**: `postman_collection/documents.postman_collection.json` documents non-existent `/document/get_documents` routes. The actual endpoints are under `/knowledge-base`.
- **⚠ Frontend/backend MIME mismatch**: UI accepts `.json` but `TextExtractionService` rejects `application/json`.
- **⚠ No RBAC, no AuditService**, no automated tests.
- **⚠ `BackgroundTasks` is non-durable**: a worker restart strands rows in `processing` with no retry mechanism.
- **⚠ Duplicate services**: `text_extractor.py` vs `text_extraction_service.py` — two implementations of the same job. Pick one.
- **⚠ Orphaned frontend service**: `frontend/src/services/knowledgeBaseService.ts` exists but the component uses `lib/api/knowledge-base.ts`. Drift risk.
- **⚠ No pgvector index** on `embedding` column — cosine-distance queries are seq-scans. Fine while corpora are small (<10k chunks); breaks at scale.
- **Replace file does NOT re-process if not implemented carefully**: must rerun the chunking + embedding pipeline. Verify.
- **`AgentKnowledgeBase` cascade**: deleting an upload removes the join row but the FK direction must be correct.
- **Concurrent upload + delete**: the background task may write chunks after the delete completes — leaves orphan chunks.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `organization_id` on `Upload` and `KnowledgeBaseChunk`.
- **AuthN**: `require_org_member`.
- **RBAC**: ⚠ none.
- **Storage**: Cloudflare R2 via `core/services/r2_storage_service.py`. Presigned URLs for download.
- **Embeddings**: OpenAI `text-embedding-3-small` (1536-dim). Org's OpenAI API key required.
- **Audit logging**: ⚠ none.
- **Observability**: standard Python `logger`; no metrics on chunk count, embedding latency, or RAG hit rate.
- **Performance**:
  - Processing happens inline in a FastAPI BackgroundTask — same process, no Celery.
  - ⚠ Embedding API calls block the worker. Could starve other requests.
  - Cosine-distance query is seq-scan without an HNSW or IVFFlat index.

## 5. Test cases (as-built)

⚠ **No dedicated test file** for KB. Block below is the locked-in behavior.

```
TEST: upload_document_happy_path
  GIVEN agent X has an agent_config
  WHEN  POST /knowledge-base (multipart: file=foo.pdf, agent_id=X)
  THEN  201; Upload row created with status='processing';
        AgentKnowledgeBase join row created;
        R2 object at uploads/{org}/{upload_id};
        BackgroundTask scheduled

TEST: upload_no_agent_config_orphans_r2
  GIVEN agent X has no agent_config
  WHEN  POST /knowledge-base
  THEN  ⚠ 409; but R2 object already written — orphan blob

TEST: ee_upload_skips_processing
  GIVEN EE controller invoked
  WHEN  POST /knowledge-base
  THEN  Upload row created with status='ready' immediately;
        no chunking, no embeddings ⚠

TEST: processing_pdf_chunks_and_embeds
  GIVEN Upload row with status='processing' and a PDF in R2
  WHEN  DocumentProcessingService.process_upload runs
  THEN  PyPDF2 extracts text;
        RecursiveCharacterTextSplitter produces N chunks;
        OpenAI embedding API called in batches of 100;
        KnowledgeBaseChunk rows inserted with pgvector embeddings;
        Upload.status = 'ready'

TEST: processing_rejects_json
  GIVEN file with content_type=application/json
  WHEN  process_upload runs
  THEN  TextExtractionService raises;
        Upload.status = 'error', error_message set

TEST: rename_document
  WHEN  PATCH /knowledge-base/{id} {"file_name": "new.pdf"}
  THEN  200; Upload.file_name updated; chunks untouched

TEST: replace_file
  WHEN  PATCH /knowledge-base/{id}/file (multipart new file)
  THEN  Old R2 blob deleted; new blob written;
        Old chunks deleted; status='processing'; new chunks generated

TEST: delete_document
  WHEN  DELETE /knowledge-base/{id}
  THEN  200; R2 blob deleted; KnowledgeBaseChunk rows deleted;
        AgentKnowledgeBase join row deleted; Upload row hard-deleted

TEST: runtime_rag_top3
  GIVEN agent X with 100 chunks
  WHEN  agent runs and LLM calls read_document tool with query Q
  THEN  document_tool_service returns top-3 chunks by cosine distance

TEST: cross_org_isolation
  GIVEN Upload U in org A; caller in org B
  WHEN  PATCH /knowledge-base/U
  THEN  404
```

## 6. Data model / DB schema

**Table: `uploads`** (`core/models/upload.py`)

| Column            | Type        | Null | Default     | Notes                                                |
|-------------------|-------------|------|-------------|------------------------------------------------------|
| id                | UUID        | NO   | `uuid4()`   | PK                                                   |
| organization_id   | UUID        | NO   | —           |                                                      |
| purpose           | VARCHAR(50) | NO   | —           | `kb_document` for this feature                       |
| file_name         | VARCHAR(255)| NO   | —           |                                                      |
| file_path         | VARCHAR(512)| NO   | —           | R2 key                                               |
| content_type      | VARCHAR(100)| YES  | —           |                                                      |
| status            | VARCHAR(20) | NO   | `'processing'` | `processing` / `ready` / `error`                  |
| error_message     | TEXT        | YES  | —           |                                                      |
| created_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |
| updated_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |

**Table: `knowledge_base_chunks`** (`core/models/knowledge_base_chunk.py`)

| Column            | Type             | Null | Default     | Notes                                                |
|-------------------|------------------|------|-------------|------------------------------------------------------|
| id                | UUID             | NO   | `uuid4()`   | PK                                                   |
| organization_id   | UUID             | NO   | —           |                                                      |
| upload_id         | UUID             | NO   | —           | FK → `uploads.id` ON DELETE CASCADE                  |
| agent_id          | UUID             | NO   | —           | FK → `agents.id`                                     |
| content           | TEXT             | NO   | —           | Chunk text (~1000 chars)                             |
| embedding         | VECTOR(1536)     | NO   | —           | pgvector — OpenAI text-embedding-3-small             |
| chunk_index       | INT              | NO   | —           | Position within document                             |
| created_at        | TIMESTAMPTZ      | NO   | `now()`     |                                                      |

**Table: `agent_knowledge_base`** (`core/models/agent_knowledge_base.py`) — many-to-many join

| Column          | Type | Null | Notes                       |
|-----------------|------|------|-----------------------------|
| id              | UUID | NO   | PK                          |
| agent_id        | UUID | NO   | FK → agents.id              |
| upload_id       | UUID | NO   | FK → uploads.id             |
| agent_config_id | UUID | YES  | FK → agent_configs.id       |

**Indexes**:
- `uploads.organization_id`
- `knowledge_base_chunks.agent_id`
- ⚠ **No pgvector index** on `knowledge_base_chunks.embedding` — should add an HNSW or IVFFlat index.

## 7. API design

All endpoints under prefix `/api/v1/knowledge-base`. Auth: JWT bearer. RBAC: ⚠ none.

| Method | Path                                | Purpose                                          |
|--------|-------------------------------------|--------------------------------------------------|
| POST   | `/knowledge-base/list`              | Paginated list with search/sort/filter           |
| POST   | `/knowledge-base`                   | Upload document (201) — multipart                |
| PATCH  | `/knowledge-base/{upload_id}`       | Rename document                                  |
| PATCH  | `/knowledge-base/{upload_id}/file`  | Replace file (re-chunks + re-embeds)             |
| DELETE | `/knowledge-base/{upload_id}`       | Delete document (cleanup R2 + chunks + join)     |

### POST /knowledge-base (multipart)

Form fields: `file=<binary>`, `agent_id=<uuid>`, `agent_config_id=<uuid>` (optional).

### Response (Upload payload via `_upload_to_payload`)

```json
{
  "id": "uuid", "organization_id": "uuid",
  "file_name": "policy.pdf", "file_path": "uploads/org/upload_id",
  "content_type": "application/pdf", "status": "processing",
  "error_message": null,
  "signed_url": "https://r2.cloudflare/...",
  "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"
}
```

### Referenced but not present

- ⚠ Postman: `/document/get_documents` documented but doesn't exist.
- ⚠ No `GET /knowledge-base/{id}/chunks` for inspecting chunks.
- ⚠ No `POST /knowledge-base/{id}/reprocess` for forcing a re-embed.

## 8. Backend implementation

- **Controller**: `core/api/v1/knowledge_base.py` — 5 routes; helpers `_resolve_org_id`, `_signed_url`, `_upload_to_payload`.
- **EE Controller**: `ee/api/v1/knowledge_base.py` — ⚠ skips processing.
- **Services**:
  - `core/services/document_processing_service.py` — orchestrates extract → chunk → embed → persist.
  - `core/services/chunking_service.py` — wraps LangChain `RecursiveCharacterTextSplitter`.
  - `core/services/embedding_service.py` — calls OpenAI embedding API in batches.
  - `core/services/text_extraction_service.py` — PDF/DOCX/TXT extractors.
  - `core/services/text_extractor.py` — ⚠ duplicate of above.
  - `core/services/r2_storage_service.py` — R2 wrapper.
  - `core/services/document_tool_service.py` — runtime RAG; registers `read_document` tool.
- **Background processing**: FastAPI `BackgroundTasks` (in-process, non-durable). No Celery.
- **No audit logging**, no metrics.

## 9. Frontend implementation

- **Route**: `/knowledge-base` — `frontend/src/app/(dashboard)/knowledge-base/page.tsx`.
- **API**:
  - `frontend/src/lib/api/knowledge-base.ts` — current source.
  - `frontend/src/services/knowledgeBaseService.ts` — ⚠ orphaned, not used.
- **Components**: upload modal, document list table, rename modal, delete confirm.
- **State**: Jotai atoms.
- **Polling**: list page likely polls every few seconds while any row is `status='processing'` so users see the flip to `ready`.

## 10. Postman collection & examples

⚠ `postman_collection/documents.postman_collection.json` documents `/document/*` paths that don't exist. Refresh.

### POST /api/v1/knowledge-base (multipart)

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@policy.pdf" \
  -F "agent_id=550e8400-..." \
  "$BASE_URL/api/v1/knowledge-base"
```

### POST /api/v1/knowledge-base/list

```json
{"page": 1, "page_size": 20, "search": "policy"}
```

```json
{
  "items": [{"id":"uuid","file_name":"policy.pdf","status":"ready","signed_url":"...","created_at":"..."}],
  "total": 1, "page": 1, "page_size": 20
}
```

### DELETE /api/v1/knowledge-base/{upload_id}

```json
{"message": "Document deleted successfully"}
```

## 11. Next steps

- [ ] ⚠ **Fix EE upload skip**: `ee/api/v1/knowledge_base.py` does not chunk/embed — uploads stay un-RAG'd. Either schedule processing like Core or document that EE uses an external pipeline.
- [ ] ⚠ **Plug R2 leak on 409**: write to R2 only AFTER `AgentConfig` precondition passes; or clean up R2 on the error branch.
- [ ] ⚠ **Refresh Postman collection**: drop `/document/get_documents`, add the actual `/knowledge-base/*` routes.
- [ ] ⚠ **Unify text-extraction services**: delete `text_extractor.py` (duplicate of `text_extraction_service.py`).
- [ ] ⚠ **Resolve FE service drift**: keep `lib/api/knowledge-base.ts` or `services/knowledgeBaseService.ts`, not both.
- [ ] ⚠ **Switch BackgroundTasks → Celery**: durable retries on worker restart.
- [ ] ⚠ **Add pgvector index** on `knowledge_base_chunks.embedding` (HNSW or IVFFlat).
- [ ] ⚠ **Add RBAC**: upload/delete should require admin.
- [ ] ⚠ **Add audit logging** for upload/rename/replace/delete.
- [ ] ⚠ **Reject JSON or add a JSON extractor** — the FE accepts `.json` but the backend doesn't.
- [ ] **Add tests** under `tests/test_knowledge_base.py`.
- [ ] **Add `POST /knowledge-base/{id}/reprocess`** for re-embedding after model upgrades.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) EE controller skips chunking/embedding — uploads are never RAG-indexed; (2) R2 leak on 409 path; (3) Postman collection documents non-existent `/document/get_documents`; (4) FE/BE MIME mismatch (`.json` accepted in UI, rejected in extractor); (5) `BackgroundTasks` non-durable — worker restart strands rows in `processing`; (6) Duplicate `text_extractor.py` vs `text_extraction_service.py`; (7) Orphaned frontend `services/knowledgeBaseService.ts`; (8) No pgvector index on embeddings — cosine query is seq-scan; (9) No RBAC, no audit logging, no tests.
