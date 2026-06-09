'use client';

import { motion } from 'framer-motion';
import { usePathname } from 'next/navigation';

import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/shared';
import { SoundStage } from '@/components/auth/sound-stage';

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ── visual stage (left) ─────────────────────────────────────────── */}
      <SoundStage />

      {/* ── form (right) ────────────────────────────────────────────────── */}
      <div className="relative flex flex-1 flex-col">
        {/* mobile header — the stage is hidden on small screens */}
        <div className="flex items-center justify-between px-6 py-6 lg:justify-end lg:px-10 lg:py-8">
          <div className="lg:hidden">
            <Logo size="md" />
          </div>
          <ThemeToggle />
        </div>

        <div className="flex flex-1 items-center justify-center overflow-y-auto px-6 pb-16">
          <motion.div
            key={pathname}
            className="w-full max-w-[380px]"
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

        {/* corner registration mark — a quiet "designed" detail */}
        <div className="pointer-events-none absolute bottom-6 right-8 hidden font-mono text-[10px] tracking-widest text-muted-foreground/40 lg:block">
          TONE / AUTH
        </div>
      </div>
    </div>
  );
}
