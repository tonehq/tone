import { ACCESS_TOKEN, LOGIN_DATA, ROUTE_LOGIN, TENANT_ID } from '@/constants';
import { showToast } from '@/utils/toast';

export const REFRESH_TOKEN = 'refresh_token';
const USER_ID = 'user_id';
const REDIRECT_QUERY_PARAM = 'redirect';

const isBrowser = () => typeof window !== 'undefined';

export function getAccessToken(): string | null {
  return isBrowser() ? localStorage.getItem(ACCESS_TOKEN) : null;
}

export function getRefreshToken(): string | null {
  return isBrowser() ? localStorage.getItem(REFRESH_TOKEN) : null;
}

export function setTokens({
  accessToken,
  refreshToken,
}: {
  accessToken: string;
  refreshToken?: string | null;
}) {
  if (!isBrowser()) return;
  localStorage.setItem(ACCESS_TOKEN, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN, refreshToken);
}

export function clearAuthStorage() {
  if (!isBrowser()) return;
  localStorage.removeItem(ACCESS_TOKEN);
  localStorage.removeItem(REFRESH_TOKEN);
  localStorage.removeItem(TENANT_ID);
  localStorage.removeItem(LOGIN_DATA);
  localStorage.removeItem(USER_ID);
  sessionStorage.clear();
}

function isOnLoginRoute(): boolean {
  return isBrowser() && window.location.pathname.startsWith(ROUTE_LOGIN);
}

function buildLoginUrl(preserveReturnUrl: boolean): string {
  if (!preserveReturnUrl || !isBrowser()) return ROUTE_LOGIN;
  const returnTo = `${window.location.pathname}${window.location.search}`;
  if (!returnTo || returnTo === '/' || returnTo.startsWith(ROUTE_LOGIN)) return ROUTE_LOGIN;
  return `${ROUTE_LOGIN}?${REDIRECT_QUERY_PARAM}=${encodeURIComponent(returnTo)}`;
}

export interface EndSessionOptions {
  reason?: 'expired' | 'manual' | 'unauthorized';
  notify?: boolean;
  preserveReturnUrl?: boolean;
}

/**
 * Marks an error as already handled by the auth layer so downstream error
 * handlers (e.g. `handleApiError`) can skip showing a duplicate toast.
 */
export function markAuthHandled<T>(error: T): T {
  if (error && typeof error === 'object') {
    (error as unknown as { authHandled?: boolean }).authHandled = true;
  }
  return error;
}

export function isAuthHandled(error: unknown): boolean {
  return !!(
    error &&
    typeof error === 'object' &&
    (error as { authHandled?: boolean }).authHandled === true
  );
}

/**
 * Single entry point for tearing down a session: clears storage, optionally
 * notifies the user, and redirects to login (preserving the current path so
 * the user lands back where they were after signing in).
 */
export function endSession({
  reason = 'expired',
  notify = true,
  preserveReturnUrl = true,
}: EndSessionOptions = {}) {
  clearAuthStorage();
  if (!isBrowser()) return;

  if (notify && reason !== 'manual' && !isOnLoginRoute()) {
    const title = reason === 'expired' ? 'Session expired' : 'You have been signed out';
    showToast.warning(title, 'Please log in again to continue.');
  }

  if (!isOnLoginRoute()) {
    window.location.href = buildLoginUrl(preserveReturnUrl);
  }
}
