import ThemeRegistry from '@/components/ThemeRegistry';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: 'Voice AI Dashboard',
  description: 'Manage your AI voice agents',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '32x32', type: 'image/png' },
      { url: '/icon.png', sizes: '192x192', type: 'image/png' },
    ],
    apple: '/icon.png',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${mono.variable} font-sans antialiased`}>
        <ThemeRegistry>
          <TooltipProvider>{children}</TooltipProvider>
        </ThemeRegistry>
      </body>
    </html>
  );
}
