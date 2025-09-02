import "./globals.scss";
import Head from "next/head";
import { ConfigProvider } from "antd";
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-inter',
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={inter.className}>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: "#6366f1", // Purple primary color from screenshot
              colorSuccess: "#10b981", 
              colorWarning: "#f59e0b", 
              colorBorder: "#e5e7eb",
              colorText: "#1f2937",
              colorTextSecondary: "#6b7280",
              fontFamily: inter.style.fontFamily,
              borderRadius: 8,
            },
          }}
        >
          <div>{children}</div>
        </ConfigProvider>
      </body>
    </html>
  );
}