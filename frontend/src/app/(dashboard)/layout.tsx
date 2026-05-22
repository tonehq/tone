'use client';

import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Sidebar } from '@/components/layout/sidebar';
import { AppLoader, ErrorBoundary } from '@/components/shared';
import { ACCESS_TOKEN } from '@/constants';
import { NavigationProvider, useNavigation } from '@/contexts/navigation';
import { getAssociatedTenants } from '@/services/organizationService';
import { useAuthStore } from '@/stores/auth';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hydrate = useAuthStore((s) => s.hydrate);
  const setOrganizations = useAuthStore((s) => s.setOrganizations);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const token = localStorage.getItem(ACCESS_TOKEN);
    if (!token) {
      router.replace('/login');
      return;
    }
    hydrate();
    setReady(true);

    // Pull the full list of orgs the user belongs to and seed the auth store
    // so the sidebar switcher shows every workspace, not just the active one.
    (async () => {
      try {
        const orgs = await getAssociatedTenants({ page: 1, page_size: 200 });
        setOrganizations(orgs.map((o) => ({ id: o.id, name: o.name, role: o.role })));
      } catch {
        // Sidebar will gracefully fall back to "one workspace" copy.
      }
    })();
  }, [hydrate, router, setOrganizations]);

  if (!ready) return <AppLoader />;

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
          <motion.div
            className="flex-1 flex flex-col min-h-0 min-w-0 outline-none"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {children}
          </motion.div>
        </main>
      </motion.div>
    </div>
  );
}
