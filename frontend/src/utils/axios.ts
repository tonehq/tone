import Axios from 'axios';

import { ACCESS_TOKEN, BACKEND_URL, LOGIN_DATA, ROUTE_LOGIN, TENANT_ID } from '@/constants';

const REFRESH_TOKEN = 'refresh_token';

const axiosInstance = Axios.create({
  baseURL: BACKEND_URL,
  headers: { 'Content-Type': 'application/json' },
});

axiosInstance.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem(ACCESS_TOKEN);
    if (token) config.headers.Authorization = `Bearer ${token}`;
    const tenantId = localStorage.getItem(TENANT_ID);
    if (tenantId) config.headers['tenant_id'] = tenantId;
  }
  return config;
});

let isRefreshing = false;
let queue: { resolve: (token: string) => void; reject: (err: unknown) => void }[] = [];

function flushQueue(error: unknown, token: string | null) {
  queue.forEach(({ resolve, reject }) => {
    if (error || !token) reject(error);
    else resolve(token);
  });
  queue = [];
}

function clearAuthStorage() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN);
  localStorage.removeItem(REFRESH_TOKEN);
  localStorage.removeItem(TENANT_ID);
  localStorage.removeItem(LOGIN_DATA);
  localStorage.removeItem('user_id');
}

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error?.response?.status;
    // Only skip the refresh dance for the refresh endpoint itself — any other
    // /auth/* call (e.g. /auth/change-password) must still be eligible for the
    // silent token refresh.
    const isRefreshRoute =
      typeof original?.url === 'string' && original.url.startsWith('/auth/refresh');

    if (status !== 401 || original._retry || isRefreshRoute) {
      return Promise.reject(error);
    }

    if (typeof window === 'undefined') {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem(REFRESH_TOKEN);
    if (!refreshToken) {
      clearAuthStorage();
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = ROUTE_LOGIN;
      }
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        queue.push({ resolve, reject });
      })
        .then((token) => {
          original.headers = original.headers || {};
          original.headers.Authorization = `Bearer ${token}`;
          original._retry = true;
          return axiosInstance(original);
        })
        .catch((err) => Promise.reject(err));
    }

    original._retry = true;
    isRefreshing = true;
    try {
      const { data } = await Axios.post(`${BACKEND_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const newAccess = data?.access_token;
      if (!newAccess) throw new Error('No access_token in refresh response');
      localStorage.setItem(ACCESS_TOKEN, newAccess);
      if (data?.refresh_token) localStorage.setItem(REFRESH_TOKEN, data.refresh_token);
      flushQueue(null, newAccess);
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${newAccess}`;
      return axiosInstance(original);
    } catch (refreshErr) {
      flushQueue(refreshErr, null);
      clearAuthStorage();
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = ROUTE_LOGIN;
      }
      return Promise.reject(refreshErr);
    } finally {
      isRefreshing = false;
    }
  },
);

export default axiosInstance;
