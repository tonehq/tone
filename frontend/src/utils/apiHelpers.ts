import axiosInstance from '@/utils/axios';

// Shared HTTP boilerplate for the service layer — one implementation each so
// `/…/list` bodies and multipart uploads don't re-copy the same loops/headers.

/**
 * Strip `undefined` / `null` / empty-string values out of a params object so a
 * request body (or query) only carries meaningful keys. Used by every
 * `POST /…/list` builder and query-param builder in `src/services`.
 */
export const pruneParams = <T extends object>(params: T): Record<string, unknown> => {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') out[k] = v;
  }
  return out;
};

/**
 * POST a single file as `multipart/form-data` under the `file` field.
 *
 * The axios instance defaults `Content-Type` to `application/json`; we override
 * to `multipart/form-data` with NO explicit boundary so axios/the browser fills
 * in the correct `boundary=...` — otherwise FastAPI can't parse the body and
 * returns `{loc: ["body","file"], msg: "Field required"}`.
 */
export const postMultipart = async <T>(url: string, file: File): Promise<T> => {
  const form = new FormData();
  form.append('file', file);
  const res = await axiosInstance.post<T>(url, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};
