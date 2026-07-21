'use client';

import { motion } from 'framer-motion';

import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/shared';

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <motion.div
        className="flex items-center justify-between border-b border-border p-6"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <Logo size="md" />
        <ThemeToggle />
      </motion.div>
      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-2xl">{children}</div>
      </main>
    </div>
  );
}
