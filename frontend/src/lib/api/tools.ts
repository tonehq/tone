import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { Tool } from '@/types/tool';
import axios from '@/utils/axios';

export interface PaginatedTools {
  items: Tool[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListToolsParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  tool_type?: string;
  is_active?: boolean;
}

export const TOOLS_QUERY_KEY = 'tools';

export const toolsApi = {
  list: async (params: ListToolsParams = {}): Promise<PaginatedTools> => {
    const body: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') body[key] = value;
    }
    const { data } = await axios.post<PaginatedTools>('/tool/list', body);
    return data;
  },
  delete: async (id: string): Promise<void> => {
    await axios.delete('/tool/delete_tool', { params: { tool_id: id } });
  },
};

export function useTools(params: ListToolsParams = {}) {
  return useQuery({
    queryKey: [TOOLS_QUERY_KEY, params],
    queryFn: () => toolsApi.list(params),
    placeholderData: (prev) => prev,
    // The create/edit flow upserts via Jotai atoms and does not invalidate this
    // cache, so always refetch on mount to pick up changes when returning to the
    // list page (otherwise the 30s global staleTime serves stale data).
    refetchOnMount: 'always',
  });
}

export function useDeleteTool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => toolsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [TOOLS_QUERY_KEY] }),
  });
}
