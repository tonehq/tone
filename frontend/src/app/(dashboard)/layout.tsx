'use client';

import { motion } from 'framer-motion';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { Sidebar } from '@/components/layout/sidebar';
import { AppLoader, ErrorBoundary } from '@/components/shared';
import { LOGIN_DATA, ROUTE_ONBOARDING } from '@/constants';
import { NavigationProvider, useNavigation } from '@/contexts/navigation';
import { authApi } from '@/lib/api/auth';
import { getAssociatedTenants } from '@/services/organizationService';
import { useAuthStore } from '@/stores/auth';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hydrate = useAuthStore((s) => s.hydrate);
  const setLoginResponse = useAuthStore((s) => s.setLoginResponse);
  const setOrganizations = useAuthStore((s) => s.setOrganizations);
  const setOrganization = useAuthStore((s) => s.setOrganization);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [ready, setReady] = useState(false);
  // Guard against React StrictMode double-invoke firing the org fetch twice in dev.
  const orgFetchStarted = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    // Route protection is enforced server-side by src/middleware.ts (reads the
    // httpOnly access cookie). Here we only hydrate the readable session state.
    hydrate();
    setReady(true);

    if (orgFetchStarted.current) return;
    orgFetchStarted.current = true;

    // NB: results are written to the Zustand module store (not component
    // state), so we intentionally do NOT gate them behind an AbortController —
    // under React StrictMode's dev double-invoke that would discard the fetch
    // result and leave the switcher stuck on "one workspace" until a reload.
    (async () => {
      // If the readable profile is missing but the cookie let us past the
      // middleware (e.g. localStorage was cleared), rebuild it from /me so the
      // sidebar has a user to show.
      if (!useAuthStore.getState().user) {
        try {
          const user = await authApi.me();
          if (user) setLoginResponse({ user, organizations: [] });
        } catch (err) {
          console.warn('[dashboard] /me hydrate failed', err);
        }
      }

      // Org record + org list are independent — fetch in parallel so first
      // paint isn't blocked on the onboarding gate check. The redirect is
      // applied as soon as the org record lands, regardless of the list.
      const [orgResult, orgsResult] = await Promise.allSettled([
        authApi.myOrg(),
        getAssociatedTenants({ page: 1, page_size: 200 }),
      ]);

      if (orgResult.status === 'fulfilled' && orgResult.value) {
        const org = orgResult.value;
        setOrganization(org);
        if (org.onboarding_completed === false) {
          router.replace(ROUTE_ONBOARDING);
          return;
        }
      } else if (orgResult.status === 'rejected') {
        console.warn('[dashboard] /organization/me failed', orgResult.reason);
      }

      if (orgsResult.status === 'fulfilled') {
        setOrganizations(orgsResult.value.map((o) => ({ id: o.id, name: o.name, role: o.role })));
      } else {
        console.warn('[dashboard] getAssociatedTenants failed', orgsResult.reason);
      }
    })();
  }, [hydrate, setLoginResponse, setOrganization, setOrganizations, router]);

  // Cross-tab logout sync: when another tab clears the readable session
  // (logout), mirror that here so this tab does not stay "logged in" visually
  // while the session is dead server-side.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onStorage = (e: StorageEvent) => {
      if (e.key === LOGIN_DATA && !e.newValue) {
        clearAuth();
        router.replace('/login');
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [clearAuth, router]);

  if (!ready) return <AppLoader label="Loading workspace" />;

  return (
    <NavigationProvider>
      <DashboardShell>
        <ErrorBoundary>{children}</ErrorBoundary>
      </DashboardShell>
    </NavigationProvider>
  );
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  const { sidebarWidth } = useNavigation();
  const pathname = usePathname();

  // Settings and the agent create/edit editor are focused, full-screen
  // experiences that supply their own navigation rail — hide the primary app
  // sidebar/chrome while inside them.
  const isFocused =
    pathname.startsWith('/settings') ||
    pathname.startsWith('/contacts') ||
    pathname.startsWith('/agents/create') ||
    pathname.startsWith('/agents/edit') ||
    /^\/workflows\/[^/]+/.test(pathname) ||
    /^\/call-history\/[^/]+/.test(pathname);
  if (isFocused) {
    return <div className="h-screen w-screen overflow-hidden">{children}</div>;
  }

  return (
    <div className="h-screen overflow-hidden flex">
      <Sidebar />
      <motion.div
        className="flex-1 flex flex-col h-screen min-w-0"
        initial={false}
        animate={{ marginLeft: sidebarWidth }}
        transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <main className="flex-1 p-6 overflow-auto flex flex-col min-h-0 min-w-0">
          {/* Page-entry animation uses opacity only — animating `y` would set
              `transform` on this wrapper and break `position: sticky` for any
              page that wants a sticky header. */}
          <motion.div
            className="flex-1 flex flex-col min-h-0 min-w-0 outline-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {children}
          </motion.div>
        </main>
      </motion.div>
    </div>
  );
}
