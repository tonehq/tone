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
  const { data } = await axios.post<T[] | ListResponse<T>>(url, body);
  // Accept either the bare-array legacy shape or the future envelope shape.
  if (Array.isArray(data)) return data;
  return data?.rows ?? [];
}

export async function pagedListRequest<T>(
  url: string,
  body: ListRequest = {},
): Promise<ListResponse<T>> {
  const { data } = await axios.post<T[] | ListResponse<T>>(url, body);
  if (Array.isArray(data)) {
    return {
      rows: data,
      total: data.length,
      page: body.page ?? 1,
      page_size: body.page_size ?? data.length,
    };
  }
  return data;
}
