import { useMutation, useQueryClient } from '@tanstack/react-query';

import { contactKeys } from '@/lib/api/queryKeys';
import { toListBody, usePaginatedList } from '@/lib/api/usePaginatedList';
import type {
  ContactDatasource,
  CreateDatasourcePayload,
  ListDatasourcesParams,
} from '@/types/contactDatasource';
import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';
import axios from '@/utils/axios';

/** Combined params for the datasource list (paging + optional directory scoping). */
export type ListDatasourcesQuery = PaginatedListParams & ListDatasourcesParams;

/** Thin typed wrapper over the `/contact-datasources` endpoints. */
export const datasourcesApi = {
  list: async (
    params: ListDatasourcesQuery = {},
  ): Promise<PaginatedResponse<ContactDatasource>> => {
    const { data } = await axios.post<PaginatedResponse<ContactDatasource>>(
      '/contact-datasources/list',
      toListBody(params),
    );
    return data;
  },
  create: async (payload: CreateDatasourcePayload): Promise<ContactDatasource> => {
    const { data } = await axios.post<ContactDatasource>('/contact-datasources', payload);
    return data;
  },
  remove: async (id: string): Promise<{ ok: boolean }> => {
    const { data } = await axios.delete<{ ok: boolean }>(`/contact-datasources/${id}`);
    return data;
  },
};

/** Paginated datasource list (optionally scoped to one directory). */
export function useDatasourcesList(params: ListDatasourcesQuery = {}) {
  return usePaginatedList<ContactDatasource>(
    contactKeys.datasources.list(params),
    () => datasourcesApi.list(params),
    params,
  );
}

export function useCreateDatasource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDatasourcePayload) => datasourcesApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.datasources.lists() }),
  });
}

export function useDeleteDatasource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => datasourcesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.datasources.lists() }),
  });
}
