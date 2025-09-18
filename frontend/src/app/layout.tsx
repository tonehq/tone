'use client';

import Sidebar from '@/components/Shared/SidebarComponent';
import { useState } from 'react';
import './globals.css';

import { initToast } from '@/utils/showToast';
import { ConfigProvider } from 'antd';
import { usePathname } from 'next/navigation';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [sidebar, setSidebar] = useState<boolean>(true);
  const pathname = usePathname();
  const toastHolder = initToast();

  const hideSidebar = pathname.startsWith('/auth');

  return (
    <html lang="en">
      <body>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: '#1D4ED8',
              colorSuccess: '#52c41a',
              colorWarning: '#faad14',
              colorBorder: '#e2e8f0',
              colorBorderSecondary: '#cccbcb',
              colorText: '#111827',
              borderRadius: 8,
              fontSize: 16,
            },
          }}
        >
          {toastHolder}
          <div className="flex">
            {!hideSidebar && <Sidebar sidebar={sidebar} setSidebar={setSidebar} />}
            <div style={{ width: '100vw', height: '100vh' }}>{children}</div>
          </div>
        </ConfigProvider>
      </body>
    </html>
  );
}
