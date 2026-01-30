'use client';

import { useState } from 'react';

import CustomLayout from '@/components/shared/CustomLayout';
import Sidebar from '@/components/shared/SidebarComponent';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarExpanded, setIsSidebarExpanded] = useState<boolean>(true);
  return (
    <CustomLayout
      siderWidth={isSidebarExpanded ? '16%' : '6%'}
      isSidebarExpanded={isSidebarExpanded}
      sidebarContent={
        <Sidebar
          isSidebarExpanded={isSidebarExpanded}
          setIsSidebarExpanded={setIsSidebarExpanded}
        />
      }
    >
      {children}
    </CustomLayout>
  );
}
