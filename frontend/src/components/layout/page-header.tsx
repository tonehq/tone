'use client';

import { motion } from 'framer-motion';

/**
 * PageHeader — the shared editorial header for dashboard pages.
 *
 * Mono index kicker + tight Bricolage display title, mirroring the auth
 * surface so the whole app reads as one designed system.
 */
export function PageHeader({
  index,
  kicker,
  title,
  description,
  actions,
}: {
  index?: string;
  kicker: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mb-3 flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          {index && (
            <>
              <span className="text-primary">{index}</span>
              <span className="h-px w-8 bg-border" />
            </>
          )}
          <span>{kicker}</span>
        </div>
        <h1
          className="text-[2rem] font-semibold leading-[1.04] tracking-[-0.03em] text-foreground"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </motion.div>

      {actions && (
        <motion.div
          className="flex shrink-0 items-center gap-2"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
        >
          {actions}
        </motion.div>
      )}
    </div>
  );
}
