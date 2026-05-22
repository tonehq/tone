'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface NavigationContextValue {
  breadcrumbs: BreadcrumbItem[];
  setBreadcrumbs: (items: BreadcrumbItem[]) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  sidebarWidth: number;
}

const STORAGE_KEY = 'sidebar-collapsed';
const EXPANDED_WIDTH = 240;
const COLLAPSED_WIDTH = 60;

const NavigationContext = createContext<NavigationContextValue | null>(null);

export function NavigationProvider({ children }: { children: React.ReactNode }) {
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'true') setSidebarCollapsed(true);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  const value = useMemo<NavigationContextValue>(
    () => ({
      breadcrumbs,
      setBreadcrumbs,
      sidebarCollapsed,
      toggleSidebar,
      sidebarWidth: sidebarCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH,
    }),
    [breadcrumbs, sidebarCollapsed, toggleSidebar],
  );

  return <NavigationContext.Provider value={value}>{children}</NavigationContext.Provider>;
}

export function useNavigation() {
  const ctx = useContext(NavigationContext);
  if (!ctx) throw new Error('useNavigation must be used within NavigationProvider');
  return ctx;
}
