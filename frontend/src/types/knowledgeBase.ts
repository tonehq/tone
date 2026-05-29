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
