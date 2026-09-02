'use client';

import { motion } from 'framer-motion';
import { usePathname } from 'next/navigation';

import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/shared';
import { BrandPanel } from '@/components/auth/brand-panel';

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="grid h-screen overflow-hidden bg-background lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1fr)]">
      <BrandPanel />

      <div className="relative flex min-h-0 flex-col overflow-y-auto">
        <div className="flex shrink-0 items-center justify-between px-6 py-5 sm:px-8 lg:justify-end">
          <div className="lg:hidden">
            <Logo size="md" />
          </div>
          <ThemeToggle />
        </div>

        <div className="flex flex-1 items-center justify-center px-6 pb-16 sm:px-8 lg:px-14">
          <motion.div
            key={pathname}
            className="w-full max-w-[384px]"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: { opacity: 0 },
              visible: { opacity: 1, transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
            }}
          >
            {children}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
