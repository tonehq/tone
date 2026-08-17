// Ingestion configs — named, reusable pipeline recipes (parser / tokeniser /
// embedder / vector store) that users pick when starting a new ingestion run.
// Selecting one snapshots every recipe field onto the resulting run row.

export interface IngestionConfig {
  id: string;
  name: string;
  description: string | null;
  parser: string;
  parser_config: Record<string, unknown> | null;
  tokeniser: string;
  tokeniser_config: Record<string, unknown> | null;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  embedding_version: string | null;
  embedding_config: Record<string, unknown> | null;
  vector_store: string;
  vector_store_ref: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateIngestionConfigPayload {
  name: string;
  description?: string | null;
  parser: string;
  parser_config?: Record<string, unknown> | null;
  tokeniser: string;
  tokeniser_config?: Record<string, unknown> | null;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  embedding_version?: string | null;
  embedding_config?: Record<string, unknown> | null;
  vector_store: string;
  vector_store_ref?: Record<string, unknown> | null;
  is_active?: boolean;
}

export type UpdateIngestionConfigPayload = Partial<CreateIngestionConfigPayload>;

export interface ListIngestionConfigsParams {
  page_no?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  is_active_only?: boolean;
}

export interface PaginatedIngestionConfigs {
  data: IngestionConfig[];
  total: number;
  page_no: number;
  page_size: number;
}
