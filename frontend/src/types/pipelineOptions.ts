// Mirrors GET /knowledge-base/pipeline-options
// (core/api/v1/knowledge_base_routes.py:671).
export interface PipelineOptions {
  parsers: string[];
  tokenisers: string[];
  embedders: string[];
  vector_stores: string[];
  defaults: {
    parser: string;
    tokeniser: string;
    embedding_provider: string;
    embedding_model: string;
    embedding_dimensions: number;
    vector_store: string;
  };
}

// Mirrors POST /knowledge-base/{upload_id}/runs body. Any field omitted
// falls back to the server-side defaults resolved by
// IngestionRunService.resolve_run_config.
// MVP omits parser_config / tokeniser_config / vector_store_ref /
// embedding_version — power-user JSON config is a follow-up.
// When ingestion_config_id is set, the backend snapshots every recipe field
// from the saved IngestionConfig and ignores individual field overrides
// (per product decision — a saved config is a fixed recipe).
export interface CreateIngestionRunPayload {
  ingestion_config_id?: string;
  parser?: string;
  tokeniser?: string;
  embedding_provider?: string;
  embedding_model?: string;
  embedding_dimensions?: number;
  vector_store?: string;
}

// Mirrors the 202 response body of POST /knowledge-base/{upload_id}/runs.
export interface CreateIngestionRunResponse {
  upload_id: string;
  ingestion_run_id: string;
  job_id: number;
  ingestion_config_id: string | null;
  run_config: Record<string, unknown>;
  status: string;
}
