import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { contactKeys } from '@/lib/api/queryKeys';
import { toListBody, usePaginatedList } from '@/lib/api/usePaginatedList';
import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';
import {
  CONTACT_SYNC_TERMINAL_STATUSES,
  type ContactSync,
  type CreateContactSyncPayload,
  type ListContactSyncsParams,
} from '@/types/contactSync';
import axios from '@/utils/axios';

/** Combined params for the sync list (paging/sort + optional directory scoping). */
export type ListContactSyncsQuery = Omit<PaginatedListParams, 'search'> & ListContactSyncsParams;

/** Thin typed wrapper over the `/contact-syncs` endpoints. */
export const contactSyncsApi = {
  /**
   * Create + enqueue a sync from an uploaded CSV. Sent as multipart `FormData`; the
   * response is the pending sync — poll `get(id)` until it reaches a terminal status.
   */
  create: async (payload: CreateContactSyncPayload): Promise<ContactSync> => {
    const form = new FormData();
    form.append('directory_id', payload.directory_id);
    form.append('schema_id', payload.schema_id);
    if (payload.agent_id) form.append('agent_id', payload.agent_id);
    form.append('file', payload.file);
    const { data } = await axios.post<ContactSync>('/contact-syncs', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  list: async (params: ListContactSyncsQuery = {}): Promise<PaginatedResponse<ContactSync>> => {
    const { data } = await axios.post<PaginatedResponse<ContactSync>>(
      '/contact-syncs/list',
      toListBody(params),
    );
    return data;
  },
  get: async (id: string): Promise<ContactSync> => {
    const { data } = await axios.get<ContactSync>(`/contact-syncs/${id}`);
    return data;
  },
};

/** Paginated sync list (optionally scoped to one directory). */
export function useContactSyncsList(params: ListContactSyncsQuery = {}) {
  return usePaginatedList<ContactSync>(
    contactKeys.syncs.list(params),
    () => contactSyncsApi.list(params),
    params,
  );
}

/**
 * A single sync, polled while it is still running. Once the sync reaches a terminal
 * status (`completed`/`failed`) polling stops. Enabled only when `id` is set.
 */
export function useContactSync(id: string | null | undefined, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: contactKeys.syncs.detail(id ?? ''),
    queryFn: () => contactSyncsApi.get(id as string),
    enabled: !!id,
    refetchInterval: (query) => {
      if (!options?.poll) return false;
      const status = query.state.data?.status;
      if (status && CONTACT_SYNC_TERMINAL_STATUSES.includes(status)) return false;
      return 2000;
    },
  });
}

export function useCreateContactSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateContactSyncPayload) => contactSyncsApi.create(payload),
    onSuccess: (_data, payload) => {
      qc.invalidateQueries({ queryKey: contactKeys.syncs.lists() });
      qc.invalidateQueries({ queryKey: contactKeys.contacts.lists(payload.directory_id) });
    },
  });
}
