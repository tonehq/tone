export interface KnowledgeBaseDocument {
  id: number;
  uuid: string;
  upload_id: number;
  agent_id: number;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  url: string;
  status: 'processing' | 'ready' | 'failed';
  meta_data: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}
