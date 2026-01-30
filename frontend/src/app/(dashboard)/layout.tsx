'use client';

import { useState } from 'react';

import CustomLayout from '@/components/shared/CustomLayout';
import Sidebar from '@/components/shared/SidebarComponent';

import Cookies from 'js-cookie';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarExpanded, setIsSidebarExpanded] = useState<boolean>(true);
  const org_tenant_id = Cookies.get('org_tenant_id');
  return (
    <CustomLayout
      siderWidth={isSidebarExpanded ? '16%' : '6%'}
      isSidebarExpanded={isSidebarExpanded}
      sidebarContent={
        <Sidebar
          isSidebarExpanded={isSidebarExpanded}
          setIsSidebarExpanded={setIsSidebarExpanded}
          organization_id={org_tenant_id}
        />
      }
    >
      {children}
    </CustomLayout>
  );
}
