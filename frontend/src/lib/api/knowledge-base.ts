import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import axios from '@/utils/axios';

export interface PaginatedDocuments {
  items: KnowledgeBaseDocument[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListDocumentsParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  agent_id?: string;
  status?: KnowledgeBaseDocument['status'] | '';
}

export const KNOWLEDGE_BASE_QUERY_KEY = 'knowledge-base';

export const knowledgeBaseApi = {
  list: async (params: ListDocumentsParams = {}): Promise<PaginatedDocuments> => {
    const body: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') body[key] = value;
    }
    const { data } = await axios.post<PaginatedDocuments>('/knowledge-base/list', body);
    return data;
  },
  upload: async (agentId: string | null, file: File): Promise<KnowledgeBaseDocument> => {
    const formData = new FormData();
    if (agentId) formData.append('agent_id', agentId);
    formData.append('file', file);
    const { data } = await axios.post<KnowledgeBaseDocument>('/knowledge-base', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  rename: async (id: string, fileName: string): Promise<KnowledgeBaseDocument> => {
    const { data } = await axios.patch<KnowledgeBaseDocument>(`/knowledge-base/${id}`, {
      file_name: fileName,
    });
    return data;
  },
  replaceFile: async (
    id: string,
    file: File,
    fileName?: string,
  ): Promise<KnowledgeBaseDocument> => {
    const formData = new FormData();
    formData.append('file', file);
    if (fileName) formData.append('file_name', fileName);
    const { data } = await axios.patch<KnowledgeBaseDocument>(
      `/knowledge-base/${id}/file`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return data;
  },
  delete: async (id: string): Promise<void> => {
    await axios.delete(`/knowledge-base/${id}`);
  },
};

export function useKnowledgeBase(params: ListDocumentsParams = {}) {
  return useQuery({
    queryKey: [KNOWLEDGE_BASE_QUERY_KEY, params],
    queryFn: () => knowledgeBaseApi.list(params),
    placeholderData: (prev) => prev,
  });
}

export function useUploadKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, file }: { agentId: string | null; file: File }) =>
      knowledgeBaseApi.upload(agentId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] }),
  });
}

export function useRenameKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, fileName }: { id: string; fileName: string }) =>
      knowledgeBaseApi.rename(id, fileName),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] }),
  });
}

export function useReplaceKnowledgeBaseFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file, fileName }: { id: string; file: File; fileName?: string }) =>
      knowledgeBaseApi.replaceFile(id, file, fileName),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] }),
  });
}

export function useDeleteKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => knowledgeBaseApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] }),
  });
}
