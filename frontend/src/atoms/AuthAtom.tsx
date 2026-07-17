import { atom } from 'jotai';

import { authApi } from '@/lib/api/auth';
import { LOGIN_DATA, TENANT_ID } from '@/constants';
import { abortAuthRefresh } from '@/utils/axios';
import { endSession } from '@/utils/authSession';

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

const logoutAtom = atom(null, async (_get, set) => {
  set(authAtom, (prev) => ({ ...prev, isLoading: true }));
  // Reject any requests waiting on an in-flight token refresh so they don't
  // hang forever once the session ends below.
  abortAuthRefresh();
  try {
    // The refresh token is an httpOnly cookie sent automatically; the backend
    // reads it to revoke the session row and clears both auth cookies.
    await authApi.logout();
  } catch (error) {
    // Logout is best-effort on the server; we still log the user out locally.
    console.error('Logout error:', error);
  } finally {
    set(authAtom, { user: null, isAuthenticated: false, isLoading: false });
    endSession({ reason: 'manual', preserveReturnUrl: false });
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
