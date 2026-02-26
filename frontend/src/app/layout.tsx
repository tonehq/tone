import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import ThemeRegistry from '@/components/ThemeRegistry';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: 'Voice AI Dashboard',
  description: 'Manage your AI voice agents',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${mono.variable} font-sans antialiased`}>
        <ThemeRegistry>{children}</ThemeRegistry>
      </body>
    </html>
  );
}
