import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { listKnowledgeBase } from '@/services/knowledgeBaseService';
import type { ListKnowledgeBaseParams } from '@/services/knowledgeBaseService';
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
  // Loose string: the value comes from KNOWLEDGE_BASE_STATUS_OPTIONS and is
  // filtered server-side. '' / 'all' / undefined mean "no status filter".
  status?: string;
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
  upload: async (
    agentId: string | null,
    file: File,
    ingestionConfigId?: string | null,
  ): Promise<KnowledgeBaseDocument> => {
    const formData = new FormData();
    if (agentId) formData.append('agent_id', agentId);
    if (ingestionConfigId) formData.append('ingestion_config_id', ingestionConfigId);
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
  reprocess: async (id: string): Promise<KnowledgeBaseDocument> => {
    const { data } = await axios.post<KnowledgeBaseDocument>(`/knowledge-base/${id}/reprocess`);
    return data;
  },
  delete: async (id: string): Promise<void> => {
    await axios.delete(`/knowledge-base/${id}`);
  },
};

const PROCESSING_POLL_INTERVAL_MS = 4000;

export function useKnowledgeBase(params: ListDocumentsParams = {}) {
  return useQuery({
    queryKey: [KNOWLEDGE_BASE_QUERY_KEY, params],
    queryFn: () => knowledgeBaseApi.list(params),
    placeholderData: (prev) => prev,
    refetchInterval: (query) =>
      query.state.data?.items.some((doc) => doc.status === 'processing')
        ? PROCESSING_POLL_INTERVAL_MS
        : false,
  });
}

/**
 * KB uploads for the agent Knowledge step. Wraps the `listKnowledgeBase`
 * service (which returns the richer `KnowledgeBaseUpload` shape — including the
 * transient `pending` status the agent step renders) so the step reads server
 * state from TanStack Query instead of a `useState` + `useEffect` fetch, while
 * keeping its existing item type. `placeholderData` keeps the previous page on
 * screen while a new search refetches, mirroring the old imperative refresh.
 */
export function useKnowledgeBaseUploads(params: ListKnowledgeBaseParams = {}) {
  return useQuery({
    queryKey: [KNOWLEDGE_BASE_QUERY_KEY, 'uploads', params],
    queryFn: () => listKnowledgeBase(params),
    placeholderData: (prev) => prev,
  });
}

export function useUploadKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      agentId,
      file,
      ingestionConfigId,
    }: {
      agentId: string | null;
      file: File;
      ingestionConfigId?: string | null;
    }) => knowledgeBaseApi.upload(agentId, file, ingestionConfigId),
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

export function useReprocessKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => knowledgeBaseApi.reprocess(id),
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
