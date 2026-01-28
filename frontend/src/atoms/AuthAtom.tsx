import { atom } from 'jotai';
import Cookies from 'js-cookie';

import { ACCESS_TOKEN, TENANT_ID } from '@/constants';

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

  try {
    Cookies.remove(ACCESS_TOKEN);
    Cookies.remove(TENANT_ID);
    Cookies.remove('user_id');
    Cookies.remove('login_data');

    localStorage.removeItem('auth');
    localStorage.removeItem('user');
    sessionStorage.clear();

    set(authAtom, {
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });

    window.location.href = '/auth/login';
  } catch (error) {
    console.error('Logout error:', error);
    set(authAtom, (prev) => ({ ...prev, isLoading: false }));

    Cookies.remove(ACCESS_TOKEN);
    Cookies.remove(TENANT_ID);
    Cookies.remove('user_id');
    Cookies.remove('login_data');
    window.location.href = '/auth/login';
  }
});

const getCurrentUserAtom = atom(null, (_get, set) => {
  try {
    const loginData = Cookies.get('login_data');
    const tenantId = Cookies.get(TENANT_ID);
    if (loginData) {
      const parsedData = JSON.parse(loginData);

      const currentOrgId = tenantId ? parseInt(tenantId, 10) : null;
      const organizations = parsedData.organizations || [];
      const currentOrg = currentOrgId
        ? organizations.find((org: any) => org.id === currentOrgId)
        : organizations[0];

      const user: User = {
        id: parsedData.user_id || '',
        email: parsedData.email || '',
        username: parsedData.username || '',
        first_name: parsedData.first_name || '',
        last_name: parsedData.last_name || '',
        role: currentOrg?.role || undefined,
      };

      set(authAtom, {
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    }
  } catch (error) {
    console.error('Error getting current user:', error);
    set(authAtom, {
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }
});

export { authAtom, getCurrentUserAtom, logoutAtom };
export type { AuthState, User };
