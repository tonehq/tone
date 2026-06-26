import { atom } from 'jotai';

import { authApi } from '@/lib/api/auth';
import { ACCESS_TOKEN, LOGIN_DATA, ROUTE_LOGIN, TENANT_ID } from '@/constants';

const REFRESH_TOKEN = 'refresh_token';

interface User {
  id: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  role?: 'owner' | 'admin' | 'member' | 'viewer';
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const authAtom = atom<AuthState>({
  user: null,
  isAuthenticated: false,
  isLoading: false,
});

function clearAuthStorage() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN);
  localStorage.removeItem(REFRESH_TOKEN);
  localStorage.removeItem(TENANT_ID);
  localStorage.removeItem(LOGIN_DATA);
  localStorage.removeItem('user_id');
  sessionStorage.clear();
}

const logoutAtom = atom(null, async (_get, set) => {
  set(authAtom, (prev) => ({ ...prev, isLoading: true }));
  // Capture the refresh token BEFORE clearing storage so we can hand it to
  // the backend, which uses it to revoke the matching session row.
  const refreshToken = typeof window !== 'undefined' ? localStorage.getItem(REFRESH_TOKEN) : null;
  try {
    if (refreshToken) {
      await authApi.logout({ refresh_token: refreshToken });
    }
  } catch (error) {
    // Logout is best-effort on the server; we still log the user out locally.
    console.error('Logout error:', error);
  } finally {
    clearAuthStorage();
    set(authAtom, { user: null, isAuthenticated: false, isLoading: false });
    if (typeof window !== 'undefined') {
      window.location.href = ROUTE_LOGIN;
    }
  }
});

const getCurrentUserAtom = atom(null, (_get, set) => {
  try {
    if (typeof window === 'undefined') return;
    const loginDataRaw = localStorage.getItem(LOGIN_DATA);
    const tenantId = localStorage.getItem(TENANT_ID);
    if (loginDataRaw) {
      const parsedData = JSON.parse(loginDataRaw);
      const currentOrgId = tenantId ? tenantId : null;
      const organizations = parsedData.organizations || [];
      const currentOrg = currentOrgId
        ? organizations.find((org: any) => String(org.id) === String(currentOrgId))
        : organizations[0];

      const user: User = {
        id: String(parsedData.user_id ?? ''),
        email: parsedData.email || '',
        username: parsedData.username || '',
        first_name: parsedData.profile?.first_name || parsedData.first_name || '',
        last_name: parsedData.profile?.last_name || parsedData.last_name || '',
        role: currentOrg?.role || undefined,
      };

      set(authAtom, { user, isAuthenticated: true, isLoading: false });
    }
  } catch (error) {
    console.error('Error getting current user:', error);
    set(authAtom, { user: null, isAuthenticated: false, isLoading: false });
  }
});

export { authAtom, getCurrentUserAtom, logoutAtom };
export type { AuthState, User };
