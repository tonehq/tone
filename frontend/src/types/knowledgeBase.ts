// Mirrors the backend `Upload.to_dict()` payload returned by the
// `/knowledge-base` endpoints (see core/models/upload.py). `agent_id` is added
// by the list endpoint from the AgentKnowledgeBase link and may be absent for
// standalone uploads.
export interface KnowledgeBaseDocument {
  id: string;
  agent_id?: string | null;
  file_name: string;
  file_type: string;
  size_bytes: number;
  purpose?: string;
  url?: string | null;
  status: 'processing' | 'ready' | 'failed';
  meta_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// Compact snapshot of the KB's currently-serving IngestionPipelineRun. Emitted
// inside `KnowledgeBase.to_dict()`. Present when a run has completed at least
// once; null while the first ingestion is still pending / running / failed.
export interface KnowledgeBaseActiveRunSummary {
  id: string;
  parser: string;
  tokeniser: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  vector_store: string;
  procrastinate_job_id: number | null;
}

// Mirrors backend `KnowledgeBase.to_dict()` (core/models/knowledge_base.py).
// Distinct from `KnowledgeBaseDocument` above, which mirrors the Upload row —
// this shape is what the KB detail / runs endpoints refer to as "the KB".
export interface KnowledgeBaseSummary {
  id: string;
  name: string;
  description: string | null;
  status: string;
  doc_type: string | null;
  ingestion_stats: Record<string, unknown>;
  meta_data: Record<string, unknown>;
  active_ingestion_pipeline_run_id: string | null;
  active_run: KnowledgeBaseActiveRunSummary | null;
  created_at: string | null;
  updated_at: string | null;
}
