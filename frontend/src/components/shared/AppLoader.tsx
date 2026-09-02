'use client';

import { motion } from 'framer-motion';

import { cn } from '@/lib/utils';

const BARS = [
  { x: 2, h: 8, y: 12, opacity: 0.35 },
  { x: 8, h: 16, y: 8, opacity: 0.6 },
  { x: 14, h: 24, y: 4, opacity: 1 },
  { x: 20, h: 14, y: 9, opacity: 0.6 },
  { x: 26, h: 6, y: 13, opacity: 0.35 },
];

export default function AppLoader({ label, className }: { label?: string; className?: string }) {
  return (
    <div
      role="status"
      aria-label={label ?? 'Loading'}
      className={cn('flex min-h-screen flex-col items-center justify-center gap-4', className)}
    >
      <svg viewBox="0 0 32 32" className="h-10 w-10 text-primary" aria-hidden>
        {BARS.map((bar, i) => (
          <motion.rect
            key={i}
            x={bar.x}
            width={4}
            rx={2}
            fill="currentColor"
            opacity={bar.opacity}
            initial={{ y: bar.y, height: bar.h }}
            animate={{
              y: [bar.y, 6, bar.y, 10, bar.y],
              height: [bar.h, 20, bar.h, 12, bar.h],
            }}
            transition={{
              duration: 1.4,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: i * 0.12,
            }}
          />
        ))}
      </svg>

      {label && (
        <span className="font-mono text-eyebrow uppercase tracking-[0.2em] text-muted-foreground">
          {label}
        </span>
      )}
    </div>
  );
}
