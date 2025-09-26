'use client';

import { useState } from 'react';

import CustomLayout from '@/components/Shared/CustomLayout';
import Sidebar from '@/components/Shared/SidebarComponent';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarExpanded, setIsSidebarExpanded] = useState<boolean>(true);
  return (
    <CustomLayout
      siderWidth={isSidebarExpanded ? 280 : 85}
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
