/**
 * Shared list/pagination types for the Contact Directories feature.
 *
 * Every `POST /…/list` endpoint in the contacts backend returns the same envelope
 * (`{ data, total, page_no, page_size }`) and accepts the same paging/search/sort
 * params, so both live here and are reused by every contacts api client +
 * `usePaginatedList`. (Kept separate from the older `types/list.ts`, whose `page`/`rows`
 * shape does NOT match the contacts backend's `page_no`/`data`.)
 */

/** The uniform envelope returned by every contacts `POST /…/list` endpoint. */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page_no: number;
  page_size: number;
}

/** Sort order accepted by every contacts list endpoint (`^(asc|desc)$` on the backend). */
export type ContactSortOrder = 'asc' | 'desc';

/**
 * The common query params every contacts list endpoint accepts. Individual endpoints
 * may add their own scoping fields (e.g. `directory_id`) on top of these.
 */
export interface PaginatedListParams {
  page_no?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: ContactSortOrder;
}
