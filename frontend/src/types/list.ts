/**
 * Shared list-endpoint contract.
 *
 * Any backend route that returns a paginated/filterable collection accepts
 * `ListRequest` as its body. Use the `listRequest()` helper from
 * `@/services/listHelpers` so every call uses the same shape.
 */

export type SortOrder = 'asc' | 'desc';

export interface ListRequest {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: SortOrder;
  filters?: Record<string, unknown>;
}

/** Optional envelope — used by endpoints that opt into server pagination. */
export interface ListResponse<T> {
  rows: T[];
  total: number;
  page: number;
  page_size: number;
}

export const DEFAULT_LIST_REQUEST: Required<Omit<ListRequest, 'search' | 'sort_by'>> & {
  search?: string;
  sort_by?: string;
} = {
  page: 1,
  page_size: 50,
  sort_order: 'desc',
  filters: {},
};
