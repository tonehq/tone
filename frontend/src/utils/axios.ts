import Axios, { AxiosError, AxiosRequestConfig } from 'axios';

import { BACKEND_URL, TENANT_ID } from '@/constants';
import { endSession, markAuthHandled } from '@/utils/authSession';

interface RetriableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

// Pre-auth endpoints: a 401 here is a credential/token error, not an expired
// session, so it must NOT trigger the silent-refresh flow.
const NON_REFRESHABLE_PREFIXES = [
  '/auth/login',
  '/auth/signup',
  '/auth/refresh',
  '/auth/signin-code',
  '/auth/forgot-password',
  '/auth/forget-password',
  '/auth/reset-password',
  '/auth/verify-email',
  '/auth/accept-invitation',
  '/auth/validate-invitation',
];

const axiosInstance = Axios.create({
  baseURL: BACKEND_URL,
  headers: { 'Content-Type': 'application/json' },
  // Access + refresh JWTs live in httpOnly cookies; withCredentials makes the
  // browser attach them (and store rotated ones) on every cross-origin call.
  withCredentials: true,
});

axiosInstance.interceptors.request.use((config) => {
  // No Authorization header — the token rides in the httpOnly cookie. We only
  // attach the non-sensitive active-org hint so the backend can scope the
  // tenant (it re-verifies membership before honouring it).
  if (typeof window !== 'undefined') {
    const tenantId = localStorage.getItem(TENANT_ID);
    if (tenantId) config.headers['tenant_id'] = tenantId;
  }
  return config;
});

interface QueueEntry {
  resolve: () => void;
  reject: (err: unknown) => void;
}

let isRefreshing = false;
let queue: QueueEntry[] = [];

function resolveQueue() {
  const pending = queue;
  queue = [];
  pending.forEach(({ resolve }) => resolve());
}

function rejectQueue(error: unknown) {
  const pending = queue;
  queue = [];
  pending.forEach(({ reject }) => reject(error));
}

function enqueueRefreshWaiter(): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    queue.push({ resolve, reject });
  });
}

/**
 * Called from the manual logout flow so any requests waiting on an in-flight
 * refresh don't hang after the session ends. Safe to call at any time.
 */
export function abortAuthRefresh(error?: unknown) {
  rejectQueue(error ?? new Error('Auth session ended'));
  isRefreshing = false;
}

async function refreshSession(): Promise<void> {
  // The refresh token is an httpOnly cookie — nothing to send in the body. The
  // backend reads it from the cookie and sets a rotated cookie pair on the
  // response; there are no tokens for JS to store.
  await Axios.post(`${BACKEND_URL}/auth/refresh`, {}, { withCredentials: true });
}

function retryOriginal(config: RetriableRequestConfig) {
  config._retry = true;
  return axiosInstance(config);
}

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = (error.config || {}) as RetriableRequestConfig;
    const status = error.response?.status;

    // A 401 from a pre-auth endpoint (login, signup, refresh, code/reset flows)
    // means bad credentials or an invalid token — NOT an expired session — so it
    // must surface to the caller instead of triggering a silent refresh (which
    // would fail and needlessly tear the session down). Authenticated /auth/*
    // calls (change-password, me, switch_organization) stay refreshable.
    const url = typeof original.url === 'string' ? original.url : '';
    const skipRefresh = NON_REFRESHABLE_PREFIXES.some((p) => url.startsWith(p));

    if (status !== 401 || skipRefresh) {
      return Promise.reject(error);
    }

    // Second 401 after we already retried with a fresh cookie means the new
    // token was also rejected — the session is unusable, log the user out
    // instead of surfacing a raw error.
    if (original._retry) {
      endSession({ reason: 'unauthorized' });
      return Promise.reject(markAuthHandled(error));
    }

    if (typeof window === 'undefined') {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      try {
        await enqueueRefreshWaiter();
        return retryOriginal(original);
      } catch (waiterErr) {
        return Promise.reject(waiterErr);
      }
    }

    isRefreshing = true;
    try {
      await refreshSession();
      resolveQueue();
      return retryOriginal(original);
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
