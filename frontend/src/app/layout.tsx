'use client';

// eslint-disable-next-line import/order
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';

import '@/styles/variables.css';
import './globals.css';

import { muiTheme } from '@/theme/muiTheme';

import { ToastProvider } from '@/utils/showToast';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider options={{ enableCssLayer: true }}>
          <ThemeProvider theme={muiTheme}>
            <CssBaseline />
            <ToastProvider>
              <div className="h-screen w-screen">{children}</div>
            </ToastProvider>
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
