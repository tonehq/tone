import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { contactKeys } from '@/lib/api/queryKeys';
import { toListBody, usePaginatedList } from '@/lib/api/usePaginatedList';
import type { PaginatedListParams } from '@/types/contactList';
import type {
  ContactDirectory,
  ContactDirectoryListItem,
  CreateDirectoryPayload,
  DirectoryDeleteImpact,
  DirectoryDeleteResult,
  UpdateDirectoryPayload,
} from '@/types/contactDirectory';
import type { PaginatedResponse } from '@/types/contactList';
import axios from '@/utils/axios';

/** Thin typed wrapper over the `/contact-directories` endpoints (no `any`). */
export const directoriesApi = {
  list: async (
    params: PaginatedListParams = {},
  ): Promise<PaginatedResponse<ContactDirectoryListItem>> => {
    const { data } = await axios.post<PaginatedResponse<ContactDirectoryListItem>>(
      '/contact-directories/list',
      toListBody(params),
    );
    return data;
  },
  get: async (id: string): Promise<ContactDirectory> => {
    const { data } = await axios.get<ContactDirectory>(`/contact-directories/${id}`);
    return data;
  },
  create: async (payload: CreateDirectoryPayload): Promise<ContactDirectory> => {
    const { data } = await axios.post<ContactDirectory>('/contact-directories', payload);
    return data;
  },
  update: async (id: string, payload: UpdateDirectoryPayload): Promise<ContactDirectory> => {
    const { data } = await axios.patch<ContactDirectory>(`/contact-directories/${id}`, payload);
    return data;
  },
  deleteImpact: async (id: string): Promise<DirectoryDeleteImpact> => {
    const { data } = await axios.get<DirectoryDeleteImpact>(
      `/contact-directories/${id}/delete-impact`,
    );
    return data;
  },
  remove: async (id: string): Promise<DirectoryDeleteResult> => {
    const { data } = await axios.delete<DirectoryDeleteResult>(`/contact-directories/${id}`);
    return data;
  },
};

/** Paginated directory list (each row carries a live `contact_count`). */
export function useDirectoriesList(
  params: PaginatedListParams = {},
  options?: { enabled?: boolean },
) {
  return usePaginatedList<ContactDirectoryListItem>(
    contactKeys.directories.list(params),
    () => directoriesApi.list(params),
    params,
    options,
  );
}

/** A single directory (enabled only once an id is known). */
export function useDirectory(id: string | null | undefined) {
  return useQuery({
    queryKey: contactKeys.directories.detail(id ?? ''),
    queryFn: () => directoriesApi.get(id as string),
    enabled: !!id,
  });
}

/** Delete-impact counts for the confirm modal (fetched lazily when `id` is set). */
export function useDirectoryDeleteImpact(id: string | null | undefined) {
  return useQuery({
    queryKey: contactKeys.directories.deleteImpact(id ?? ''),
    queryFn: () => directoriesApi.deleteImpact(id as string),
    enabled: !!id,
  });
}

export function useCreateDirectory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDirectoryPayload) => directoriesApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.directories.lists() }),
  });
}

export function useUpdateDirectory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateDirectoryPayload }) =>
      directoriesApi.update(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: contactKeys.directories.lists() });
      qc.invalidateQueries({ queryKey: contactKeys.directories.detail(id) });
    },
  });
}

export function useDeleteDirectory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => directoriesApi.remove(id),
    // Only refresh the lists (rail drops the deleted row). Do NOT invalidate
    // `all()` — that matches the still-mounted `detail(id)`/`deleteImpact(id)`
    // queries for the just-deleted directory and refetches them → 404. Those
    // idle queries GC on navigation away.
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.directories.lists() }),
  });
}
