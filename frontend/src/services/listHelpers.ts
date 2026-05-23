/**
 * Single entry point for calling any backend list endpoint.
 *
 *   const rows = await listRequest<MyRow>('/some/list/endpoint', { search: 'foo' });
 *
 * Endpoints that opt into server pagination can use `pagedListRequest()`,
 * which returns the `{ rows, total, page, page_size }` envelope.
 */

import type { ListRequest, ListResponse } from '@/types/list';
import axios from '@/utils/axios';

export async function listRequest<T>(url: string, body: ListRequest = {}): Promise<T[]> {
  const { data } = await axios.post<T[] | ListResponse<T> | { data: T[] }>(url, body);
  // Accept bare-array, { rows: [...] } envelope, or { data: [...] } envelope.
  if (Array.isArray(data)) return data;
  if ('rows' in data && Array.isArray(data.rows)) return data.rows;
  if ('data' in data && Array.isArray(data.data)) return data.data;
  return [];
}

export async function pagedListRequest<T>(
  url: string,
  body: ListRequest = {},
): Promise<ListResponse<T>> {
  const { data } = await axios.post<
    | T[]
    | ListResponse<T>
    | { data: T[]; pagination: { total: number; page: number; page_size: number } }
  >(url, body);
  if (Array.isArray(data)) {
    return {
      rows: data,
      total: data.length,
      page: body.page ?? 1,
      page_size: body.page_size ?? data.length,
    };
  }
  // Handle { data: [...], pagination: {...} } envelope from backend
  if ('data' in data && 'pagination' in data) {
    const d = data as { data: T[]; pagination: { total: number; page: number; page_size: number } };
    return {
      rows: d.data,
      total: d.pagination.total,
      page: d.pagination.page,
      page_size: d.pagination.page_size,
    };
  }
  return data as ListResponse<T>;
}
