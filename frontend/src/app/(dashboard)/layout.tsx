'use client';

import Sidebar from '@/components/shared/SidebarComponent';
import { Box } from '@mui/material';
import React, { useState } from 'react';

const _DRAWER_WIDTH = 240;
const _COLLAPSED_WIDTH = 72;

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  return (
    <Box sx={{ display: 'flex', gap: 2, width: '100vw', minHeight: '100vh' }}>
      <Box sx={{ width: sidebarExpanded ? 240 : 72 }}>
        <Sidebar
          isExpanded={sidebarExpanded}
          onToggle={() => setSidebarExpanded((prev) => !prev)}
        />
        <button onClick={() => setSidebarExpanded((prev) => !prev)}>{'<'}</button>
      </Box>

      <Box
        sx={{
          width: sidebarExpanded ? 'calc(100vw - 240px)' : 'calc(100vw - 72px)',
          backgroundColor: '#f9fafb',
          minHeight: '100vh',
          transition: 'margin-left 0.3s ease',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
