import { useMutation, useQueryClient } from '@tanstack/react-query';

import { contactKeys } from '@/lib/api/queryKeys';
import { toListBody, usePaginatedList } from '@/lib/api/usePaginatedList';
import type {
  BulkDeleteContactsResponse,
  Contact,
  ContactListResponse,
  CreateContactsPayload,
  CreateContactsResponse,
  ListContactsParams,
  ScheduleContactCallsPayload,
  ScheduleContactCallsResponse,
  UpdateContactPayload,
} from '@/types/contact';
import axios from '@/utils/axios';

/**
 * Directory-scoped contacts client. Every list/create/bulk-delete route is nested under
 * `/contact-directories/{directoryId}`; single-contact update/delete address by contact
 * id (the backend still directory-scopes the lookup). Create is bulk + partial (C-7).
 */
export const contactsApi = {
  list: async (
    directoryId: string,
    params: ListContactsParams = {},
  ): Promise<ContactListResponse> => {
    const { data } = await axios.post<ContactListResponse>(
      `/contact-directories/${directoryId}/contacts/list`,
      toListBody(params),
    );
    return data;
  },
  /**
   * Create one or many contacts (partial success). Returns `{ created, failed }` (C-7) —
   * callers must handle `failed[]` (per-row `{ index, errors }`), not assume a single
   * contact came back.
   */
  create: async (
    directoryId: string,
    payload: CreateContactsPayload,
  ): Promise<CreateContactsResponse> => {
    const { data } = await axios.post<CreateContactsResponse>(
      `/contact-directories/${directoryId}/contacts`,
      payload,
    );
    return data;
  },
  update: async (id: string, payload: UpdateContactPayload): Promise<Contact> => {
    const { data } = await axios.patch<Contact>(`/contacts/${id}`, payload);
    return data;
  },
  remove: async (id: string): Promise<void> => {
    await axios.delete(`/contacts/${id}`);
  },
  bulkDelete: async (directoryId: string, ids: string[]): Promise<BulkDeleteContactsResponse> => {
    const { data } = await axios.post<BulkDeleteContactsResponse>(
      `/contact-directories/${directoryId}/contacts/bulk-delete`,
      { ids },
    );
    return data;
  },
  scheduleCalls: async (
    payload: ScheduleContactCallsPayload,
  ): Promise<ScheduleContactCallsResponse> => {
    const { data } = await axios.post<ScheduleContactCallsResponse>(
      '/contact/schedule-calls',
      payload,
    );
    return data;
  },
};

/** Paginated contacts for one directory. `poll` surfaces rows landing from a live sync. */
export function useContactsList(
  directoryId: string | null | undefined,
  params: ListContactsParams = {},
  options?: { poll?: boolean },
) {
  return usePaginatedList<Contact>(
    contactKeys.contacts.list(directoryId ?? '', params),
    () => contactsApi.list(directoryId as string, params),
    params,
    {
      enabled: !!directoryId,
      refetchInterval: options?.poll ? 4000 : false,
    },
  );
}

export function useCreateContacts(directoryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateContactsPayload) => contactsApi.create(directoryId, payload),
    onSuccess: (_data, payload) => {
      qc.invalidateQueries({ queryKey: contactKeys.contacts.lists(directoryId) });
      qc.invalidateQueries({ queryKey: contactKeys.directories.lists() });
      // Create-and-assign (payload carries `agent_id`) also mutates that agent's contact
      // list server-side, so refetch it too.
      if (payload.agent_id) {
        qc.invalidateQueries({ queryKey: contactKeys.agentContacts.lists(payload.agent_id) });
      }
    },
  });
}

export function useUpdateContact(directoryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateContactPayload }) =>
      contactsApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.contacts.lists(directoryId) }),
  });
}

export function useDeleteContact(directoryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => contactsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: contactKeys.contacts.lists(directoryId) });
      qc.invalidateQueries({ queryKey: contactKeys.directories.lists() });
    },
  });
}

export function useBulkDeleteContacts(directoryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => contactsApi.bulkDelete(directoryId, ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: contactKeys.contacts.lists(directoryId) });
      qc.invalidateQueries({ queryKey: contactKeys.directories.lists() });
    },
  });
}

export function useScheduleContactCalls() {
  return useMutation({
    mutationFn: (payload: ScheduleContactCallsPayload) => contactsApi.scheduleCalls(payload),
  });
}

export type { Contact };
