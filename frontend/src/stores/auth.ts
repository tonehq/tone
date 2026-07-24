import { create } from 'zustand';

import { LOGIN_DATA, TENANT_ID } from '@/constants';
import type { AuthLoginResponse, Organization, User, UserOrganization } from '@/types/auth';

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

// Persist the membership list into the readable login_data payload so a page
// reload rebuilds the workspace switcher from localStorage instantly, instead
// of showing "one workspace" until the async fetch returns. The login response
// itself does not carry the full org list — it's fetched after login.
function persistOrganizations(orgs: UserOrganization[]) {
  if (typeof window === 'undefined') return;
  const loginData = readJSON<AuthLoginResponse>(LOGIN_DATA);
  if (!loginData) return;
  localStorage.setItem(LOGIN_DATA, JSON.stringify({ ...loginData, organizations: orgs }));
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
  // payload when no membership row carried one. (The JWT is now an httpOnly
  // cookie JS can't read, so role always comes from the login response body.)
  if (user && !user.role) {
    user.role = (loginData?.role as string) ?? null;
  }

  // The tokens live in httpOnly cookies; the presence of the readable
  // login_data payload is our client-side signal that a session exists. The
  // authoritative gate is the server-side Next.js middleware (which reads the
  // cookie) plus per-request 401 handling.
  return {
    user,
    organization,
    organizations,
    activeOrgId: activeOrgId || organization?.id || null,
    isAuthenticated: !!loginData,
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
      // Tokens are set as httpOnly cookies by the server; we persist only the
      // non-sensitive profile/org payload for UI hydration.
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
    set((s) => {
      // active_org_id (the tenant) is owned EXCLUSIVELY by explicit login /
      // workspace-switch / logout / hydrate. Refreshing the current org's
      // *record* (name, onboarding flags, …) from a background
      // GET /organization/me must NEVER repoint the tenant — otherwise the
      // dashboard silently switches orgs a few seconds after first paint.
      if (!s.activeOrgId) {
        // First run / onboarding: no tenant chosen yet — adopt this org.
        if (typeof window !== 'undefined' && org?.id) {
          localStorage.setItem(TENANT_ID, org.id);
        }
        return { organization: org, activeOrgId: org?.id ?? null };
      }
      // A tenant is already active: only refresh the record for that SAME org,
      // and never rewrite active_org_id. Ignore a mismatched record so a stale
      // or wrong response can't flip the UI to another workspace.
      if (org && String(org.id) === String(s.activeOrgId)) {
        return { organization: org };
      }
      return {};
    });
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
            name:
              s.organizations.find((o) => String(o.id) === String(orgId))?.name ??
              s.organization?.name ??
              '',
          }
        : null,
    }));
  },
  setOrganizations: (orgs) => {
    // Cache the list so a reload hydrates the switcher without waiting for the
    // async fetch (the login response doesn't include it).
    persistOrganizations(orgs);
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
    });
  },
  clearAuth: () => {
    if (typeof window !== 'undefined') {
      // Only readable state — the httpOnly token cookies are cleared by the
      // backend `/auth/logout` call in the logout flow.
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
