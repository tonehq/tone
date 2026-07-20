import { useQuery, type QueryKey, type UseQueryResult } from '@tanstack/react-query';

import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';

/**
 * Generic TanStack Query hook for the contacts backend's `POST /…/list` endpoints.
 *
 * WHAT: given a stable query key, a fetcher that returns the standard
 * `{ data, total, page_no, page_size }` envelope, and the paging/search/sort params,
 * this runs the query with `placeholderData` (so page/search changes don't flash empty)
 * and an optional poll interval.
 *
 * WHEN: use it for EVERY paginated contacts list (directories, contacts, schemas, syncs,
 * assigned contacts) instead of re-wiring `useQuery` per resource. Pass the matching key
 * from `queryKeys.ts` and a client `.list` fetcher — e.g.
 *   `usePaginatedList(contactKeys.directories.list(params), () => directoriesApi.list(params), params)`.
 *
 * `params` is passed through to the fetcher's closure by the caller; it is accepted here
 * only to type the params surface and keep the call site self-documenting.
 */
export function usePaginatedList<T, P extends PaginatedListParams = PaginatedListParams>(
  queryKey: QueryKey,
  fetcher: () => Promise<PaginatedResponse<T>>,
  _params?: P,
  options?: {
    /** Refetch interval in ms while mounted (e.g. to surface in-flight imports). `false` = off. */
    refetchInterval?: number | false;
    /** Disable the query until a dependency (e.g. a selected directory id) is ready. */
    enabled?: boolean;
  },
): UseQueryResult<PaginatedResponse<T>> {
  return useQuery({
    queryKey,
    queryFn: fetcher,
    placeholderData: (prev) => prev,
    refetchInterval: options?.refetchInterval ?? false,
    enabled: options?.enabled ?? true,
  });
}

/**
 * Strip empty/undefined/null values from list params so they aren't sent as blank query
 * fields (the backend treats an absent field as "no filter"). Reused by every list
 * fetcher that POSTs a params body.
 */
export function toListBody(params: object = {}): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') body[key] = value;
  }
  return body;
}
