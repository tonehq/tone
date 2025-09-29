'use client';

import { ConfigProvider } from 'antd';

import './globals.css';

import { initToast } from '@/utils/showToast';
import '@ant-design/v5-patch-for-react-19';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const toastHolder = initToast();

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
            components: {
              Layout: {
                siderBg: '#3f3f46',
              },
              Breadcrumb: {
                separatorMargin: 4,
              },
            },
          }}
        >
          {toastHolder}
          <div className="h-screen w-screen">{children}</div>
        </ConfigProvider>
      </body>
    </html>
  );
}
