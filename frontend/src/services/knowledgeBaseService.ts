import { pruneParams } from '@/utils/apiHelpers';
import axiosInstance from '@/utils/axios';

export interface KnowledgeBaseUpload {
  id: string;
  file_name: string;
  file_type: string;
  size_bytes: number;
  purpose: string;
  status: 'pending' | 'processing' | 'ready' | 'failed' | string;
  meta_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  url?: string | null;
}

export interface ListKnowledgeBaseParams {
  search?: string;
  agent_id?: string;
  status?: 'pending' | 'processing' | 'ready' | 'failed' | 'all';
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedKnowledgeBase {
  items: KnowledgeBaseUpload[];
  total: number;
  page: number;
  page_size: number;
}

export const listKnowledgeBase = async (
  params: ListKnowledgeBaseParams = {},
): Promise<PaginatedKnowledgeBase> => {
  const body = pruneParams(params);
  const res = await axiosInstance.post<PaginatedKnowledgeBase>('/knowledge-base/list', body);
  return res.data;
};
