'use client';

import { motion } from 'framer-motion';

import { cn } from '@/lib/utils';

const BARS = [
  { x: 2, h: 8, y: 12, opacity: 0.6 },
  { x: 8, h: 16, y: 8, opacity: 0.75 },
  { x: 14, h: 24, y: 4, opacity: 0.9 },
  { x: 20, h: 14, y: 9, opacity: 0.75 },
  { x: 26, h: 6, y: 13, opacity: 0.6 },
];

export default function AppLoader({ className }: { className?: string }) {
  return (
    <div className={cn('flex min-h-screen items-center justify-center', className)}>
      <motion.div
        className="relative"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="absolute inset-0 blur-2xl opacity-20 bg-primary rounded-full scale-150" />

        <svg viewBox="0 0 32 32" className="relative h-12 w-12" aria-hidden>
          <defs>
            <linearGradient id="tone-loader-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#8b5cf6" />
            </linearGradient>
          </defs>
          {BARS.map((bar, i) => (
            <motion.rect
              key={i}
              x={bar.x}
              width={4}
              rx={2}
              fill="url(#tone-loader-grad)"
              opacity={bar.opacity}
              initial={{ y: 16, height: 0 }}
              animate={{
                y: [bar.y, 6, bar.y, 10, bar.y],
                height: [bar.h, 20, bar.h, 12, bar.h],
                opacity: [bar.opacity, 1, bar.opacity, 0.9, bar.opacity],
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
      </motion.div>
    </div>
  );
}
