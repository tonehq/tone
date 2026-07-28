// Mirrors backend `IngestionPipelineRun.to_dict()`
// (core/models/ingestion_pipeline_run.py). One row per ingestion attempt
// against an upload; multiple can co-exist so users can A/B parsers /
// tokenisers / embedders / vector stores side-by-side.
export type IngestionRunStatus = 'pending' | 'running' | 'ready' | 'failed';

export interface IngestionRun {
  id: string;
  upload_id: string;
  knowledge_base_id: string;
  run_number: number;

  parser: string;
  parser_config: Record<string, unknown> | null;
  tokeniser: string;
  tokeniser_config: Record<string, unknown> | null;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  embedding_version: string | null;
  vector_store: string;
  vector_store_ref: Record<string, unknown> | null;

  status: IngestionRunStatus;
  is_active: boolean;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  chunk_count: number | null;
  procrastinate_job_id: number | null;

  created_at: string;
  updated_at: string;
}

export interface PaginatedIngestionRuns {
  data: IngestionRun[];
  total: number;
  page_no: number;
  page_size: number;
}

export interface ListIngestionRunsParams {
  page_no?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  status_filter?: IngestionRunStatus[];
  is_active_only?: boolean;
}
