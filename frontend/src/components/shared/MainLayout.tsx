'use client';

import { useMediaQuery } from '@/hooks/useMediaQuery';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';
import { Menu } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import SidebarComponent from './SidebarComponent';

interface MainLayoutProps {
  children: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const isMobile = useMediaQuery('(max-width: 767px)');
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');

  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const hasSetTabletCollapsed = useRef(false);

  useEffect(() => {
    if (isTablet && !hasSetTabletCollapsed.current) {
      hasSetTabletCollapsed.current = true;
      setSidebarExpanded(false);
    }
  }, [isTablet]);

  const sidebarWidth = isMobile
    ? 0
    : sidebarExpanded
      ? SIDEBAR_WIDTH_EXPANDED
      : SIDEBAR_WIDTH_COLLAPSED;

  return (
    <div className="flex w-full min-h-screen">
      <SidebarComponent
        isExpanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded((prev) => !prev)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {isMobile && (
        <header className="fixed inset-x-0 top-0 z-50 flex h-14 items-center gap-3 border-b border-border bg-background px-4 shadow-sm">
          <button
            type="button"
            aria-label="Open sidebar"
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-foreground transition-colors hover:bg-muted"
          >
            <Menu size={24} />
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            T
          </div>
          <span className="text-lg font-bold text-foreground">Tone</span>
        </header>
      )}

      <main
        className="flex-1 min-h-screen overflow-auto bg-background transition-[margin-left,width] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
        style={{
          width: isMobile ? '100%' : `calc(100% - ${sidebarWidth}px)`,
          marginLeft: isMobile ? 0 : sidebarWidth,
          paddingTop: isMobile ? '3.5rem' : 0,
        }}
      >
        {children}
      </main>
    </div>
  );
}
