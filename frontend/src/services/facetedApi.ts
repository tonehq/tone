/**
 * Transport helpers for the faceted-list pattern. Each entity exposes three
 * endpoints — POST `/{entity}/list`, POST `/{entity}/facets`, and
 * GET `/{entity}/filter-values` — and these helpers normalize their responses
 * for `useFacetedList`.
 */

import type { FacetedFacetsQuery, FacetedListQuery, Facets } from '@/types/facetedList';
import axios from '@/utils/axios';

/** POST a faceted list query and normalize the envelope to `{ rows, total }`. */
export async function fetchFacetedList<T>(
  url: string,
  query: FacetedListQuery,
): Promise<{ rows: T[]; total: number }> {
  // Entity list endpoints use `page` (not call-log's `page_no`).
  const body: Record<string, unknown> = {
    page: query.page_no,
    page_size: query.page_size,
  };
  if (query.search) body.search = query.search;
  if (query.sort_by) {
    body.sort_by = query.sort_by;
    body.sort_order = query.sort_order;
  }
  if (query.filters?.length) body.filters = query.filters;

  const { data } = await axios.post(url, body);

  if (Array.isArray(data)) return { rows: data as T[], total: data.length };
  if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>;
    // { items, total } — tool / knowledge-base / agent
    if (Array.isArray(d.items)) {
      return { rows: d.items as T[], total: (d.total as number) ?? d.items.length };
    }
    // { data, pagination } — mcp-server
    if (Array.isArray(d.data) && d.pagination) {
      const total = (d.pagination as { total?: number }).total ?? (d.data as T[]).length;
      return { rows: d.data as T[], total };
    }
    if (Array.isArray(d.rows)) {
      return { rows: d.rows as T[], total: (d.total as number) ?? d.rows.length };
    }
  }
  return { rows: [], total: 0 };
}

/** POST a facets query and return the `{ field: [{ value, count }] }` map. */
export async function fetchFacets(url: string, query: FacetedFacetsQuery): Promise<Facets> {
  const { data } = await axios.post<Facets>(url, query);
  return data ?? {};
}

/** GET distinct values of a column for token-search autocomplete. */
export async function fetchFilterValues(url: string, field: string): Promise<string[]> {
  const { data } = await axios.get<{ column: string; values: string[] }>(url, {
    params: { column_name: field },
  });
  return data?.values ?? [];
}
