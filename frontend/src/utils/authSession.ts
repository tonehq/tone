import { LOGIN_DATA, ROUTE_LOGIN, TENANT_ID } from '@/constants';
import { showToast } from '@/utils/toast';

const USER_ID = 'user_id';
// Must match the query param the login page reads (`?next=`) and the one the
// Next.js middleware sets, so forced-logout returns the user to where they were.
const REDIRECT_QUERY_PARAM = 'next';

const isBrowser = () => typeof window !== 'undefined';

/**
 * Clears the JS-readable session state (user profile, active org). The access
 * and refresh tokens themselves live in httpOnly cookies that JS cannot touch;
 * those are cleared server-side by the `/auth/logout` endpoint (manual logout)
 * or simply expire.
 */
export function clearAuthStorage() {
  if (!isBrowser()) return;
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
