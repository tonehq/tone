export interface KnowledgeBaseDocument {
  id: string;
  upload_id: string;
  agent_id: string;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  url?: string | null;
  status: 'processing' | 'ready' | 'failed';
  meta_data: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}
