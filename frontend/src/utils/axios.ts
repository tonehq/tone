import Axios, { AxiosError, AxiosRequestConfig } from 'axios';

import { BACKEND_URL, TENANT_ID } from '@/constants';
import {
  endSession,
  getAccessToken,
  getRefreshToken,
  markAuthHandled,
  setTokens,
} from '@/utils/authSession';

interface RetriableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

const axiosInstance = Axios.create({
  baseURL: BACKEND_URL,
  headers: { 'Content-Type': 'application/json' },
});

axiosInstance.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (typeof window !== 'undefined') {
    const tenantId = localStorage.getItem(TENANT_ID);
    if (tenantId) config.headers['tenant_id'] = tenantId;
  }
  return config;
});

interface QueueEntry {
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}

let isRefreshing = false;
let queue: QueueEntry[] = [];

function resolveQueue(token: string) {
  const pending = queue;
  queue = [];
  pending.forEach(({ resolve }) => resolve(token));
}

function rejectQueue(error: unknown) {
  const pending = queue;
  queue = [];
  pending.forEach(({ reject }) => reject(error));
}

function enqueueRefreshWaiter(): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    queue.push({ resolve, reject });
  });
}

/**
 * Called from the manual logout flow so any requests waiting on an in-flight
 * refresh don't hang after storage is cleared. Safe to call at any time.
 */
export function abortAuthRefresh(error?: unknown) {
  rejectQueue(error ?? new Error('Auth session ended'));
  isRefreshing = false;
}

async function refreshAccessToken(refreshToken: string): Promise<string> {
  const { data } = await Axios.post(`${BACKEND_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  const newAccess = data?.access_token as string | undefined;
  if (!newAccess) throw new Error('No access_token in refresh response');
  setTokens({ accessToken: newAccess, refreshToken: data?.refresh_token ?? null });
  return newAccess;
}

function retryWithToken(config: RetriableRequestConfig, token: string) {
  config.headers = config.headers || {};
  (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  config._retry = true;
  return axiosInstance(config);
}

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = (error.config || {}) as RetriableRequestConfig;
    const status = error.response?.status;

    // Only skip the refresh dance for the refresh endpoint itself — any other
    // /auth/* call (e.g. /auth/change-password) must still be eligible for a
    // silent token refresh.
    const isRefreshRoute =
      typeof original.url === 'string' && original.url.startsWith('/auth/refresh');

    if (status !== 401 || isRefreshRoute) {
      return Promise.reject(error);
    }

    // Second 401 after we already retried with a fresh token means the new
    // token was also rejected — the session is unusable, log the user out
    // instead of surfacing a raw error.
    if (original._retry) {
      endSession({ reason: 'unauthorized' });
      return Promise.reject(markAuthHandled(error));
    }

    if (typeof window === 'undefined') {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      endSession({ reason: 'expired' });
      return Promise.reject(markAuthHandled(error));
    }

    if (isRefreshing) {
      try {
        const token = await enqueueRefreshWaiter();
        return retryWithToken(original, token);
      } catch (waiterErr) {
        return Promise.reject(waiterErr);
      }
    }

    isRefreshing = true;
    try {
      const newAccess = await refreshAccessToken(refreshToken);
      resolveQueue(newAccess);
      return retryWithToken(original, newAccess);
    } catch (refreshErr) {
      const handledErr = markAuthHandled(refreshErr);
      rejectQueue(handledErr);
      endSession({ reason: 'expired' });
      return Promise.reject(handledErr);
    } finally {
      isRefreshing = false;
    }
  },
);

export default axiosInstance;
