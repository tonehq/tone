import { useMutation, useQueryClient } from '@tanstack/react-query';

import { contactKeys } from '@/lib/api/queryKeys';
import { toListBody, usePaginatedList } from '@/lib/api/usePaginatedList';
import type {
  AgentContactRow,
  AssignContactsPayload,
  AssignContactsResult,
  UnassignContactsPayload,
  UnassignContactsResult,
} from '@/types/agentContact';
import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';
import axios from '@/utils/axios';

/** Thin typed wrapper over the `/agents/{id}/contacts/*` assignment endpoints. */
export const agentContactsApi = {
  list: async (
    agentId: string,
    params: PaginatedListParams = {},
  ): Promise<PaginatedResponse<AgentContactRow>> => {
    const { data } = await axios.post<PaginatedResponse<AgentContactRow>>(
      `/agents/${agentId}/contacts/list`,
      toListBody(params),
    );
    return data;
  },
  assign: async (
    agentId: string,
    payload: AssignContactsPayload,
  ): Promise<AssignContactsResult> => {
    const { data } = await axios.post<AssignContactsResult>(
      `/agents/${agentId}/contacts/assign`,
      payload,
    );
    return data;
  },
  unassign: async (
    agentId: string,
    payload: UnassignContactsPayload,
  ): Promise<UnassignContactsResult> => {
    const { data } = await axios.post<UnassignContactsResult>(
      `/agents/${agentId}/contacts/unassign`,
      payload,
    );
    return data;
  },
};

/** Paginated list of contacts assigned to an agent (enabled once `agentId` is set). */
export function useAgentContactsList(
  agentId: string | null | undefined,
  params: PaginatedListParams = {},
) {
  return usePaginatedList<AgentContactRow>(
    contactKeys.agentContacts.list(agentId ?? '', params),
    () => agentContactsApi.list(agentId as string, params),
    params,
    { enabled: !!agentId },
  );
}

export function useAssignContacts(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AssignContactsPayload) => agentContactsApi.assign(agentId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.agentContacts.lists(agentId) }),
  });
}

export function useUnassignContacts(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (contactIds: string[]) =>
      agentContactsApi.unassign(agentId, { contact_ids: contactIds }),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.agentContacts.lists(agentId) }),
  });
}
