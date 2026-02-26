'use client';

import React, { useState } from 'react';

import Sidebar from '../../components/shared/SidebarComponent';

const DRAWER_WIDTH = 240;
const COLLAPSED_WIDTH = 72;

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  const width = sidebarExpanded ? DRAWER_WIDTH : COLLAPSED_WIDTH;

  return (
    <div className="flex min-h-screen w-screen">
      <div className="shrink-0 transition-[width] duration-300 ease-in-out" style={{ width }}>
        <Sidebar
          isExpanded={sidebarExpanded}
          onToggle={() => setSidebarExpanded((prev) => !prev)}
        />
      </div>

      <main
        className="min-h-screen bg-background transition-[width] duration-300 ease-in-out"
        style={{ width: `calc(100vw - ${width}px)` }}
      >
        {children}
      </main>
    </div>
  );
}
