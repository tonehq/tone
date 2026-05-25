import { create } from 'zustand';

import { ACCESS_TOKEN, LOGIN_DATA, TENANT_ID } from '@/constants';
import type { AuthLoginResponse, Organization, User, UserOrganization } from '@/types/auth';
import { decodeJWT } from '@/utils/jwt';

function readRoleFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const claims = decodeJWT(token);
    return (claims?.role as string) || null;
  } catch {
    return null;
  }
}

const REFRESH_TOKEN = 'refresh_token';

interface AuthState {
  user: User | null;
  organization: Organization | null;
  organizations: UserOrganization[];
  activeOrgId: string | null;
  isAuthenticated: boolean;
  hydrate: () => void;
  setAuth: (user: User, org?: Organization | null) => void;
  setLoginResponse: (data: AuthLoginResponse) => void;
  setUser: (user: User) => void;
  setOrganization: (org: Organization | null) => void;
  setActiveOrgId: (orgId: string | null) => void;
  setOrganizations: (orgs: UserOrganization[]) => void;
  clearAuth: () => void;
}

function readJSON<T>(key: string): T | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

// Build a clean Organization + User pair from the active membership. The
// organization is rebuilt fresh (id + name only) so that fields like slug,
// logo_url, or subscription_* from a previously-active workspace can't leak
// through after a switch — those should be re-fetched from the API.
function reconcileActiveOrg(
  activeOrgId: string | null,
  orgs: UserOrganization[],
  user: User | null,
): { organization: Organization; user: User | null } | null {
  const membership = activeOrgId ? orgs.find((o) => String(o.id) === String(activeOrgId)) : null;
  if (!membership) return null;
  return {
    organization: { id: membership.id, name: membership.name },
    user: user ? { ...user, role: membership.role ?? user.role ?? null } : user,
  };
}

function bootstrap() {
  if (typeof window === 'undefined') {
    return {
      user: null,
      organization: null,
      organizations: [] as UserOrganization[],
      activeOrgId: null,
      isAuthenticated: false,
    };
  }
  const loginData = readJSON<AuthLoginResponse>(LOGIN_DATA);
  const token = localStorage.getItem(ACCESS_TOKEN);
  const activeOrgId = localStorage.getItem(TENANT_ID);

  // Prefer the new tone-test shape (user + organization objects).
  let user: User | null = (loginData?.user as User) || null;
  let organization: Organization | null = (loginData?.organization as Organization) || null;
  const organizations: UserOrganization[] = loginData?.organizations ?? [];

  // Fallback to the legacy shape (user_id + email + organizations array).
  if (!user && loginData) {
    user = {
      id: (loginData.user_id as any) ?? '',
      email: loginData.email ?? '',
      first_name: (loginData.profile as any)?.first_name ?? null,
      last_name: (loginData.profile as any)?.last_name ?? null,
      role: (loginData.profile as any)?.role ?? null,
    };
  }

  // If the user has switched workspaces, the active org id in localStorage is
  // the source of truth — reconcile organization name and per-org role with
  // the matching membership so the sidebar reflects the current tenant
  // after reload.
  const reconciled = reconcileActiveOrg(activeOrgId, organizations, user);
  if (reconciled) {
    organization = reconciled.organization;
    user = reconciled.user;
  } else if (!organization && organizations.length) {
    organization = {
      id: organizations[0].id as string,
      name: organizations[0].name ?? 'Workspace',
    };
    if (user && !user.role) user.role = organizations[0].role ?? null;
  }

  // Role is contextual to the active membership — fall back to the login
  // payload / token claims when no membership row carried one.
  if (user && !user.role) {
    user.role = (loginData?.role as string) ?? readRoleFromToken(token) ?? null;
  }

  return {
    user,
    organization,
    organizations,
    activeOrgId: activeOrgId || organization?.id || null,
    isAuthenticated: !!token,
  };
}

export const useAuthStore = create<AuthState>((set) => ({
  ...bootstrap(),
  hydrate: () => set(bootstrap()),
  setAuth: (user, org = null) => {
    if (typeof window !== 'undefined' && org?.id) {
      localStorage.setItem(TENANT_ID, org.id);
    }
    set((s) => ({
      user,
      organization: org ?? s.organization,
      isAuthenticated: true,
      activeOrgId: org?.id ?? s.activeOrgId,
    }));
  },
  setLoginResponse: (data) => {
    if (typeof window !== 'undefined') {
      if (data.access_token) localStorage.setItem(ACCESS_TOKEN, data.access_token);
      if (data.refresh_token) localStorage.setItem(REFRESH_TOKEN, data.refresh_token);
      localStorage.setItem(LOGIN_DATA, JSON.stringify(data));
      if (data.user_id != null) localStorage.setItem('user_id', String(data.user_id));
      else if (data.user?.id != null) localStorage.setItem('user_id', String(data.user.id));

      // Pick an active org id from either shape.
      const orgIdFromUser = data.organization?.id;
      const orgIdFromList = data.organizations?.[0]?.id;
      const orgId = orgIdFromUser || orgIdFromList;
      if (orgId) localStorage.setItem(TENANT_ID, String(orgId));
    }
    set({ ...bootstrap(), isAuthenticated: true });
  },
  setUser: (user) => set({ user }),
  setOrganization: (org) => {
    if (typeof window !== 'undefined' && org?.id) {
      localStorage.setItem(TENANT_ID, org.id);
    }
    set({ organization: org, activeOrgId: org?.id ?? null });
  },
  setActiveOrgId: (orgId) => {
    if (typeof window !== 'undefined') {
      if (orgId) localStorage.setItem(TENANT_ID, orgId);
      else localStorage.removeItem(TENANT_ID);
    }
    set((s) => ({
      activeOrgId: orgId,
      organization: orgId
        ? {
            id: orgId,
            name: s.organizations.find((o) => o.id === orgId)?.name ?? s.organization?.name ?? '',
          }
        : null,
    }));
  },
  setOrganizations: (orgs) =>
    set((s) => {
      // The full membership list arrives async (DashboardLayout fetches it
      // after bootstrap), so this is our first chance to reconcile the
      // displayed organization and role with the active tenant in
      // localStorage. Without this, switching workspaces + reload shows the
      // original login org until something else updates the store.
      const reconciled = reconcileActiveOrg(s.activeOrgId, orgs, s.user);
      if (!reconciled) return { organizations: orgs };
      return {
        organizations: orgs,
        organization: reconciled.organization,
        user: reconciled.user,
      };
    }),
  clearAuth: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(ACCESS_TOKEN);
      localStorage.removeItem(REFRESH_TOKEN);
      localStorage.removeItem(TENANT_ID);
      localStorage.removeItem(LOGIN_DATA);
      localStorage.removeItem('user_id');
    }
    set({
      user: null,
      organization: null,
      organizations: [],
      activeOrgId: null,
      isAuthenticated: false,
    });
  },
}));

export { REFRESH_TOKEN };
